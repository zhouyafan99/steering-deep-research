import uuid
import sys
import os

# Add the project root to sys.path to ensure imports work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.agents.research import researcher

def run_agent(agent, message: str):
    print(f"Starting research on: {message}")
    print("-" * 50)
    
    # Generate a random thread_id for this run
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # stream_mode="values" returns the state values after each step
        result = agent.stream(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            stream_mode="values",
        )

        for chunk in result:
            # chunk is a dictionary representing the state
            if "messages" in chunk:
                messages = chunk["messages"]
                if messages:
                    last_message = messages[-1]
                    last_message.pretty_print()
                    
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Allow running with a command line argument
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        # Default test query
        query = "如何宠溺小白脸？"
    
    run_agent(researcher, query)
