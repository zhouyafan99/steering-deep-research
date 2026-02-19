
import asyncio
import os
import sys
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
import uvicorn
from langchain_core.messages import HumanMessage, AIMessage
import re

def normalize_answer(ans: str) -> str:
    s = (ans or "").strip()
    if not s:
        return "B"
    up = s.upper()
    # Direct option
    m = re.search(r"\b([ABC])\b", up)
    if m:
        return m.group(1)
    # Chinese fallback
    if any(k in s for k in ["随意", "都行", "你定", "无所谓", "随便"]):
        return "B"
    # Default fallback (don't throw error)
    return "B"

# --- Project Setup ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(os.path.join(project_root, "deep-research-mini"))

from src.agents.workflow import builder
from langgraph.checkpoint.memory import MemorySaver

# --- FastAPI App Initialization ---
app = FastAPI()
sessions = {}

# --- Data Serialization Helper ---
def serialize_event(event: dict) -> dict:
    if isinstance(event, dict):
        return {key: serialize_event(value) for key, value in event.items()}
    elif isinstance(event, list):
        return [serialize_event(item) for item in event]
    elif isinstance(event, (HumanMessage, AIMessage)):
        return event.dict()
    return event

# --- WebSocket Endpoint ---
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    print(f"\n[BACKEND LOG] 1. WebSocket connection established for session: {session_id}")

    if session_id not in sessions:
        sessions[session_id] = {"checkpointer": MemorySaver()}
    
    graph = builder.compile(checkpointer=sessions[session_id]["checkpointer"])
    config = {"configurable": {"thread_id": session_id}}

    try:
        while True:
            try:
                data = await websocket.receive_json()
                print("[WS_RECV]", data)

                message_type = data.get("type")
                current_input = None

                if message_type == "start_research":
                    query = data.get("query")
                    current_input = {"messages": [HumanMessage(content=query)]}
                elif message_type == "clarify_answer":
                    raw_answer = data.get("answer")
                    normalized_answer = normalize_answer(raw_answer)
                    current_input = {"messages": [HumanMessage(content=normalized_answer)]}
                    print(f"\n[BACKEND LOG] Normalized user answer ''{raw_answer}'' to ''{normalized_answer}''")

                if current_input:
                    print(f"\n[BACKEND LOG] Invoking graph for thread_id={session_id} with input: {current_input['messages'][0].content[:50]}...")
                    async for event in graph.astream(current_input, config=config):
                        (node_name, node_output), = event.items()
                        print(f"--- Node: {node_name} ---")

                        # Check for clarification questions
                        messages = node_output.get("messages", [])
                        if messages and isinstance(messages[-1], AIMessage):
                            last_msg = messages[-1]
                            if "Please choose a research focus:" in last_msg.content:
                                response = {"type": "clarify", "content": last_msg.content}
                                await websocket.send_json(response)
                                print(f"[BACKEND LOG] Sent clarification question.")

                        # Check for plan
                        if node_name == "planner":
                            plan = node_output.get("current_plan", "")
                            if plan:
                                response = {"type": "plan", "content": plan.splitlines()}
                                await websocket.send_json(response)
                                print(f"[BACKEND LOG] Sent research plan.")
                        
                        # Check for final report
                        if node_name == "reporter":
                            messages = node_output.get("messages", [])
                            if messages:
                                report = messages[-1].content
                                response = {"type": "result", "content": report}
                                await websocket.send_json(response)
                                print(f"[BACKEND LOG] Sent final report.")
            except Exception as e:
                import traceback
                traceback.print_exc()
                await websocket.send_json({"type": "error", "message": str(e), "trace_id": session_id})
                continue



    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session: {session_id}")
        if session_id in sessions: del sessions[session_id]
    except Exception as e:
        print(f"An error occurred: {e}")
        # Add a traceback for more detailed server-side logging
        import traceback
        traceback.print_exc()
        await websocket.send_json({"type": "error", "message": f"An unexpected error occurred: {e}", "trace_id": session_id})

# --- Static Files & Root ---
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "../frontend/build/static")), name="static")

@app.route("/{full_path:path}", methods=["GET", "POST"])
async def serve_react_app(full_path: str):
    index_path = os.path.join(current_dir, "../frontend/build/index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not built. Run `npm run build`."}

# --- Main Entry Point ---
if __name__ == "__main__":
    print("Starting FastAPI server with detailed logging...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
