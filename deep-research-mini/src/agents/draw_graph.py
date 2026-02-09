import sys
import os
from langchain_core.runnables.graph import MermaidDrawMethod

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.agents.research import researcher

def draw_graph():
    print("Generating Mermaid flowchart...")
    graph = researcher.get_graph()
    
    # Generate Mermaid code
    mermaid_code = graph.draw_mermaid()
    with open("react_agent.md", "w", encoding="utf-8") as f:
        f.write("```mermaid\n")
        f.write(mermaid_code)
        f.write("\n```")
    print("Mermaid code saved to 'react_agent.md'")
    
    # Try to generate PNG using mermaid.ink API (requires internet)
    try:
        print("Attempting to generate PNG via mermaid.ink API...")
        png_bytes = graph.draw_mermaid_png()
        with open("react_agent.png", "wb") as f:
            f.write(png_bytes)
        print("Graph saved to 'react_agent.png'")
    except Exception as e:
        print(f"Could not generate PNG: {e}")
        print("Please check if you have internet access or the necessary dependencies.")

if __name__ == "__main__":
    draw_graph()
