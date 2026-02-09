import asyncio
import sys
import os
import json

# Ensure the deep-research-mini directory is in the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, "deep-research-mini"))

from src.agents.workflow import builder
from src.models import chat_model
from src.utils import apply_prompt_template
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

async def run_deep_research(user_input: str):
    print(f"🚀 Starting workflow on: {user_input}\n")
    
    # We use a thread_id to maintain state across clarification turns
    config = {"configurable": {"thread_id": "1"}}
    
    # Initialize checkpointer and compile graph locally
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    
    # Initial input
    # Note: In a real app, you might want to generate a unique thread_id per session
    current_input = {"messages": [HumanMessage(content=user_input)]}
    
    current_node = None # Track the current active node

    while True:
        collected_urls = set()
        supervisor_ran = False
        last_ai_message = None

        # Run the graph (streaming events)
        # We use astream_events to visualize progress
        async for event in graph.astream_events(current_input, version="v2", config=config):
            kind = event["event"]
            name = event["name"]
            data = event["data"]

            # Track Current Node
            if kind == "on_chain_start":
                if name in ["supervisor", "planner", "reporter", "researcher", "check_clarity"]:
                    current_node = name
            elif kind == "on_chain_end":
                if name == current_node:
                    current_node = None

            # Detect if supervisor started (meaning we passed clarification)
            if kind == "on_chain_start" and name == "supervisor":
                supervisor_ran = True
                print("\n🧠 [Supervisor] Updating Research CoT...\n")

            # --- 1. Capture: Reading articles/webpages (Tool Usage) ---

            # --- 1. Capture: Reading articles/webpages (Tool Usage) ---
            # Hidden for user experience
            if kind == "on_tool_start":
                tool_input = data.get("input")
                if name == "web_crawl":
                    url = tool_input.get("url") if isinstance(tool_input, dict) else tool_input
                    # print(f"\n🔍 [Reading] Deep reading webpage: {url}")
                    collected_urls.add(url)
                elif name == "web_search":
                    query = tool_input.get("query") if isinstance(tool_input, dict) else tool_input
                    # print(f"\n🌐 [Searching] Searching for: {query}")

            # --- 1.5 Capture: Search Results (Tool Output) ---
            elif kind == "on_tool_end" and name == "web_search":
                output = data.get("output")
                if isinstance(output, list):
                    for item in output:
                        if isinstance(item, dict) and "url" in item:
                            collected_urls.add(item["url"])
                elif isinstance(output, str):
                    try:
                        results = json.loads(output)
                        if isinstance(results, list):
                            for item in results:
                                if isinstance(item, dict) and "url" in item:
                                    collected_urls.add(item["url"])
                    except:
                        pass

            # --- 2. Capture: Planner Output (Visible) ---
            elif kind == "on_chain_end" and name == "planner":
                pass
                # output = data.get("output")
                # if output and isinstance(output, dict) and "messages" in output:
                #     messages = output["messages"]
                #     if messages and isinstance(messages[-1], AIMessage):
                #         last_msg = messages[-1]
                #         # Just print the content directly, it's already formatted by the prompt
                #         print(f"\n{last_msg.content}")

            # --- 2.5 Capture: Researcher Output (Hidden) ---
            elif kind == "on_chain_end" and name == "researcher":
                pass
                # output = data.get("output")
                # if output and isinstance(output, dict) and "messages" in output:
                #     messages = output["messages"]
                #     if messages and isinstance(messages[-1], AIMessage):
                #         print(f"\n{messages[-1].content}")
                #         print("-" * 50)
            
            # --- Capture the final output message (if any) ---
            if kind == "on_chat_model_end":
                output = data.get("output")
                if output:
                    last_ai_message = output.content

            # --- 3. Capture: Real-time streaming from the model ---
            elif kind == "on_chat_model_stream":
                # Only stream output for specific nodes
                if current_node in ["supervisor", "planner", "reporter", "check_clarity"]:
                    content = data.get("chunk", {}).content if isinstance(data.get("chunk"), dict) == False else data.get("chunk").get("content")
                    # Safety check for chunk object access
                    if "chunk" in data and hasattr(data["chunk"], "content"):
                         content = data["chunk"].content
                    
                    if content:
                        print(content, end="", flush=True)

        # After the graph run finishes:
        if supervisor_ran:
            # Research completed
            print("\n✅ Research Completed!")
            if collected_urls:
                print("\n📚 Sources used:")
                for url in collected_urls:
                    print(f"- {url}")
            break
        else:
            # Supervisor didn't run, so it must be a clarification question
            # Retrieve the latest state to get the question
            state = await graph.get_state(config)
            if state.values and state.values["messages"]:
                last_msg = state.values["messages"][-1]
                if isinstance(last_msg, AIMessage):
                    print(f"\n❓ Clarification needed: {last_msg.content}")
                    user_answer = input(">> Your answer: ")
                    
                    # Feed the answer back into the graph
                    # The graph state already has the history, so we just add the new HumanMessage
                    current_input = {"messages": [HumanMessage(content=user_answer)]}
                    # Loop continues...
                else:
                    # Should not happen if logic is correct
                    print("Error: Graph ended without supervisor and without clarification question.")
                    break
            else:
                break

if __name__ == "__main__":
    # Get user input from console
    print("Welcome to Deep Research Agent!")
    topic = input("Please enter your research topic: ")
    
    try:
        if topic.strip():
            asyncio.run(run_deep_research(topic))
        else:
            print("Empty topic provided. Exiting.")
    except KeyboardInterrupt:
        print("\n\n🛑 Process interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ An error occurred: {e}")
