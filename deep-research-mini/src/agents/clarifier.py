import asyncio
import sys
import os

# Ensure the deep-research-mini directory is in the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, "deep-research-mini"))

from src.models import chat_model
from src.utils import apply_prompt_template
from langchain_core.messages import HumanMessage

# async def test_clarifier():
#     user_input = "如何拥有神级执行力？"
#     conversation_history = "None"
    
#     print("--- 1. Rendering Prompt ---")
#     prompt_content = apply_prompt_template(
#         "clarifier", 
#         conversation_history=conversation_history, 
#         user_input=user_input
#     )
    
#     print("\n--- PROMPT CONTENT START ---")
#     print(prompt_content)
#     print("--- PROMPT CONTENT END ---\n")
    
#     print("--- 2. Invoking Model ---")
#     response = await chat_model.ainvoke([HumanMessage(content=prompt_content)])
    
#     print("\n--- MODEL RESPONSE ---")
#     print(response.content)

# if __name__ == "__main__":
#     asyncio.run(test_clarifier())