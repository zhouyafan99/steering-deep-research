
import sys
import os
sys.path.append(os.getcwd())

try:
    from langgraph.prebuilt import create_react_agent
    from src.models import chat_model
    from src.tools import web_search
    
    print("Attempting to create planner agent with 'name' parameter...")
    planner = create_react_agent(
        chat_model,
        tools=[web_search],
        name="planner"
    )
    print("✅ Successfully created planner with name")
except TypeError as e:
    print(f"❌ TypeError detected: {e}")
    print("Checking if create_react_agent accepts 'name'...")
    import inspect
    sig = inspect.signature(create_react_agent)
    print(f"Signature: {sig}")
except Exception as e:
    print(f"❌ Other error: {e}")
    import traceback
    traceback.print_exc()
