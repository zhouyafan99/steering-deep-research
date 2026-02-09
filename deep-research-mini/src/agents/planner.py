from langgraph.prebuilt import create_react_agent

from src.models import chat_model
from src.utils import apply_prompt_template
from src.tools import web_search

planner = create_react_agent(
    chat_model,
    tools=[web_search],
    prompt=apply_prompt_template("planner"),
    name="planner",
)
