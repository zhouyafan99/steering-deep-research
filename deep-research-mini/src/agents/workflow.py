from typing import Annotated, List, Literal
import sys
import os
import operator
import json

# Add the project root to sys.path if running directly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.append(project_root)
    sys.path.append(os.path.join(project_root, "deep-research-mini"))

from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage, AIMessage
from src.models import chat_model
from src.utils import apply_prompt_template
from src.tools import web_search

print("--- WORKFLOW.PY IMPORTED ---")

# Define State
class ResearchState(MessagesState):
    supervisor_cot: str
    round_count: int
    max_rounds: int
    gathered_info: Annotated[List[str], operator.add]
    current_plan: str
    supervisor_decision: str # "CONTINUE" or "TERMINATE"
    user_intervention: str

# Node 1: Check Clarity
async def check_clarity(state: ResearchState):
    """
    Analyzes the user's latest message (and history) to decide if clarification is needed.
    """
    messages = state["messages"]

    # === [Single Round Clarification Enforcement] ===
    # If we have history (User -> AI -> User...), assume the user has responded to the clarification.
    # We strictly limit clarification to 1 round to avoid loops.
    if len(messages) >= 3:
        print("[Check Clarity] Single-round limit reached. Proceeding to research.")
        return {"messages": []}
    
    # Extract the latest user input
    last_message = messages[-1]
    user_input = last_message.content
    
    # Construct conversation history
    history_msgs = messages[:-1]
    conversation_history = "\n".join([f"{m.type}: {m.content}" for m in history_msgs]) if history_msgs else "None"
    
    # Render the prompt
    prompt_content = apply_prompt_template(
        "clarifier", 
        conversation_history=conversation_history, 
        user_input=user_input
    )
    
    # Call the model
    response = await chat_model.ainvoke([HumanMessage(content=prompt_content)])
    content = response.content.strip()
    
    if not content:
        # Fallback if model returns empty content
        return {"messages": [AIMessage(content="I encountered an issue generating a response. Please try again.")]}
    
    if "CLEAR" in content.upper():
        # If clear, we don't add any new message, just proceed to supervisor
        return {"messages": []}
    elif "CHAT" in content.upper():
        # If it's just chat, generate a polite response
        chat_prompt = f"User said: {user_input}\nContext: {conversation_history}\nReply naturally and helpfully as a friendly assistant. Keep it brief."
        chat_response = await chat_model.ainvoke([HumanMessage(content=chat_prompt)])
        return {"messages": [chat_response]}
    else:
        # Return the clarification questions
        return {"messages": [response]}

def route_after_check(state: ResearchState):
    messages = state["messages"]
    last_msg = messages[-1]
    
    if isinstance(last_msg, AIMessage):
        # If check_clarity added a message (question or chat), stop.
        return END
    
    # If no message added, proceed to research.
    return "supervisor"

# Node 2: Supervisor (CoT + Evaluator)
async def supervisor(state: ResearchState):
    messages = state["messages"]
    # === [新增逻辑] 优先检查用户干预 ===
    # 检查 State 中是否有用户插入的指令
    user_intervention = state.get("user_intervention")
    
    if user_intervention:
        print(f"🚨 Supervisor 检测到用户新指令: {user_intervention}")
        
        # 1. 把新指令追加到现有的思维链(CoT)中，或者覆盖目标
        # 这里我们选择追加，让 AI 知道是"修正"
        current_cot = state.get("supervisor_cot", "")
        updated_cot = f"{current_cot}\n\n[USER INTERVENTION/CORRECTION]: {user_intervention}\n(I must update the plan immediately based on this.)"
        
        # 2. 构造一个系统消息告诉自己发生了什么（可选，为了历史记录）
        intervention_msg = AIMessage(content=f"User intervened: {user_intervention}. Re-planning...")
        
        return {
            "messages": [intervention_msg],
            "supervisor_cot": updated_cot,
            # 3. 关键：强制消费掉这个指令（置空），防止死循环
            "user_intervention": None, 
            # 4. 关键：强制设为 CONTINUE，并在路由中指向 Planner
            "supervisor_decision": "CONTINUE",
            # 重置轮次? 视情况而定，如果换方向了，最好重置一下，或者增加上限
            # "max_rounds": state.get("max_rounds", 3) + 2 
        }

    # Case 1: Initial CoT Generation
    if not state.get("supervisor_cot"):
        conversation_history = "\n".join([f"{m.type}: {m.content}" for m in messages])
        last_user_input = messages[-1].content
        
        prompt = apply_prompt_template(
            "supervisor",
            user_input=last_user_input,
            conversation_history=conversation_history,
            supervisor_cot=None
        )
        
        response = await chat_model.ainvoke([HumanMessage(content=prompt)])
        
        return {
            "messages": [response],
            "supervisor_cot": response.content,
            "round_count": 0,
            "max_rounds": 3,
            "gathered_info": [],
            "supervisor_decision": "CONTINUE"
        }
    
    # Case 2: Evaluation
    else:
        # Get the latest gathered info (from the most recent research round)
        all_gathered = state.get("gathered_info", [])
        latest_info = all_gathered[-1] if all_gathered else "None"
        
        prompt = apply_prompt_template(
            "supervisor",
            supervisor_cot=state.get("supervisor_cot", ""),
            gathered_info=latest_info,
            round_count=state.get("round_count", 0),
            max_rounds=state.get("max_rounds", 3)
        )
        
        response = await chat_model.ainvoke([HumanMessage(content=prompt)])
        
        content = response.content
        decision = "CONTINUE"
        if "Decision: TERMINATE" in content:
            decision = "TERMINATE"
            
        # Extract the updated CoT (everything before the decision)
        if "Decision:" in content:
            updated_cot = content.split("Decision:")[0].strip()
        else:
            updated_cot = content.strip()
            
        return {
            "messages": [response],
            "supervisor_cot": updated_cot,
            "supervisor_decision": decision
        }

def route_supervisor(state: ResearchState):
    decision = state.get("supervisor_decision", "CONTINUE")
    round_count = state.get("round_count", 0)
    max_rounds = state.get("max_rounds", 3)
    
    if decision == "TERMINATE" or round_count >= max_rounds:
        return "reporter"
    
    return "planner"

# Node 3: Planner
async def planner(state: ResearchState):
    current_round = state.get("round_count", 0) + 1
    
    prompt = apply_prompt_template(
        "planner_loop",
        round_count=current_round,
        max_rounds=state.get("max_rounds", 3),
        supervisor_cot=state.get("supervisor_cot", ""),
        gathered_info="\n\n".join(state.get("gathered_info", [])) if state.get("gathered_info") else "None"
    )
    
    response = await chat_model.ainvoke([HumanMessage(content=prompt)])
    
    return {
        "messages": [response],
        "current_plan": response.content,
        "round_count": current_round
    }

# Node 4: Researcher
async def researcher(state: ResearchState):
    plan = state.get("current_plan", "")
    
    # Extract queries
    extraction_prompt = f"You are a helper. Extract the search queries from this plan as a JSON list of strings. Return ONLY the JSON list (e.g. [\"query1\", \"query2\"]).\nPlan:\n{plan}"
    extraction = await chat_model.ainvoke([HumanMessage(content=extraction_prompt)])
    
    queries = []
    try:
        content = extraction.content.replace("```json", "").replace("```", "").strip()
        queries = json.loads(content)
    except:
        # Fallback parsing
        for line in plan.split("\n"):
            if "Search:" in line:
                parts = line.split("Search:")
                if len(parts) > 1:
                    queries.append(parts[1].split("->")[0].strip())
    
    if not queries:
        queries = [plan[:200]] # Fallback
        
    findings = []
    
    # Execute searches (limit 5)
    for q in queries[:5]:
        try:
            res = await web_search.ainvoke(q)
            findings.append(f"Query: {q}\nResult: {res}")
        except Exception as e:
            findings.append(f"Query: {q}\nError: {e}")
            
    combined_findings = "\n\n".join(findings)
    
    # Display message
    display_msg = f"**Researching websites...**\nExecuted {len(queries)} searches:\n"
    for q in queries[:5]:
        display_msg += f"- {q}\n"
    
    return {
        "messages": [AIMessage(content=display_msg)],
        "gathered_info": [combined_findings]
    }

# Node 5: Reporter
async def reporter(state: ResearchState):
    # Find the last user message (effective query)
    messages = state["messages"]
    user_query = "Unknown Query"
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            user_query = m.content
            break

    prompt = apply_prompt_template(
        "reporter",
        user_query=user_query,
        supervisor_cot=state.get("supervisor_cot", ""),
        gathered_info="\n\n".join(state.get("gathered_info", []))
    )
    
    response = await chat_model.ainvoke([HumanMessage(content=prompt)])
    return {"messages": [response]}

# Build Graph
builder = StateGraph(ResearchState)

builder.add_node("check_clarity", check_clarity)
builder.add_node("supervisor", supervisor)
builder.add_node("planner", planner)
builder.add_node("researcher", researcher)
builder.add_node("reporter", reporter)

builder.add_edge(START, "check_clarity")
builder.add_conditional_edges(
    "check_clarity", 
    route_after_check, 
    {END: END, "supervisor": "supervisor"}
)

builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {"planner": "planner", "reporter": "reporter"}
)

builder.add_edge("planner", "researcher")
builder.add_edge("researcher", "supervisor")
builder.add_edge("reporter", END)

# Compile
graph = builder.compile()

# Export builder for testing
__all__ = ["graph", "builder", "ResearchState"]
