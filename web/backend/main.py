
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
async def stream_graph_events(session_id: str, websocket: WebSocket, graph_input: dict):
    """Helper to stream graph events and send them to the websocket."""
    graph = sessions[session_id]["graph"]
    config = sessions[session_id]["config"]
    try:
        async for event in graph.astream(graph_input, config=config, stream_mode="updates"):
            (node_name, node_output), = event.items()
            print(f"--- Node: {node_name} ---")
            
            messages = node_output.get("messages", [])
            if messages and isinstance(messages[-1], AIMessage):
                last_msg = messages[-1]
                if node_name == "check_clarity" and "Please choose a research focus:" in last_msg.content:
                    await websocket.send_json({"type": "clarify", "content": last_msg.content})
                elif node_name == "planner":
                    plan = node_output.get("current_plan", "")
                    if plan:
                        # Use plan_updated for subsequent plans
                        event_type = "plan_updated" if sessions[session_id].get("plan_sent") else "plan"
                        await websocket.send_json({"type": event_type, "content": plan.splitlines()})
                        sessions[session_id]["plan_sent"] = True
                elif node_name == "reporter":
                    await websocket.send_json({"type": "result", "content": last_msg.content})

    except asyncio.CancelledError:
        print(f"[stream_graph_events] Task for session {session_id} was cancelled.")
    except Exception as e:
        traceback.print_exc()
        await websocket.send_json({"type": "error", "message": f"An error occurred during research: {e}"})
    finally:
        sessions[session_id]["is_running"] = False


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    print(f"\n[BACKEND LOG] WebSocket connection established for session: {session_id}")

    if session_id not in sessions:
        sessions[session_id] = {
            "checkpointer": MemorySaver(),
            "task": None,
            "is_running": False,
            "plan_sent": False,
            "graph": builder.compile(checkpointer=MemorySaver()),
            "config": {"configurable": {"thread_id": session_id}},
        }

    try:
        while True:
            data = await websocket.receive_json()
            print(f"[WS_RECV] {data}")
            message_type = data.get("type")
            
            current_task = sessions[session_id].get("task")
            if current_task:
                current_task.cancel()

            sessions[session_id]["is_running"] = True
            graph_input = None

            if message_type == "start_research":
                sessions[session_id]["plan_sent"] = False # Reset for new research
                query = data.get("query")
                graph_input = {"messages": [HumanMessage(content=query)]}
            
            elif message_type == "clarify_answer":
                raw_answer = data.get("answer")
                normalized_answer = normalize_answer(raw_answer)
                graph_input = {"messages": [HumanMessage(content=normalized_answer)]}

            elif message_type == "steer":
                instruction = data.get("instruction")
                await websocket.send_json({"type": "steer_ack", "content": f"已收到指令: '{instruction}'"})
                graph_input = {"messages": [HumanMessage(content=f"(Instruction): {instruction}")]}

            if graph_input:
                new_task = asyncio.create_task(stream_graph_events(session_id, websocket, graph_input))
                sessions[session_id]["task"] = new_task

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session: {session_id}")
    finally:
        task = sessions.get(session_id, {}).get("task")
        if task:
            task.cancel()
        if session_id in sessions:
            del sessions[session_id]
        print(f"Cleaned up session {session_id}")

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
