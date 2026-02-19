from langgraph.prebuilt import create_react_agent
from src.models import chat_model
from src.tools import web_search, web_crawl
from src.utils import apply_prompt_template

system_prompt = apply_prompt_template("research_agent")

research_agent = create_react_agent(
    model=chat_model,
    tools=[web_search, web_crawl],
    prompt=system_prompt,
    name="researcher"
)
