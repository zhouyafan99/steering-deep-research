from langchain_tavily import TavilySearch

web_search = TavilySearch(
    name="web_search",
    max_results=5,
    description="A search engine optimized for comprehensive, accurate, and trusted results. Useful for when you need to answer questions about current events. Input should be a search query string."
)
