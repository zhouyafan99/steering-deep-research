import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

api_key = os.getenv("ARK_API_KEY")
base_url = "https://ark.cn-beijing.volces.com/api/v3"

if not api_key:
    # Fallback or warning
    print("Warning: ARK_API_KEY not found in environment variables.")

chat_model = ChatOpenAI(
    model="doubao-seed-1-6-flash-250828",
    base_url=base_url,
    api_key=api_key,
    temperature=0,
)
