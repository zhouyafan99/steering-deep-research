from langgraph_supervisor import create_supervisor

from src.agents.planner import planner
from src.agents.research import researcher
from src.models import chat_model
from src.utils import apply_prompt_template

supervisor = create_supervisor(
    [planner, researcher],
    model=chat_model,
    prompt=apply_prompt_template("supervisor"),
).compile()
