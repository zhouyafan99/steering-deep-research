from langchain_core.tools import tool
from firecrawl import FirecrawlApp
import os

@tool
def web_crawl(url: str):
    """
    Useful for crawling a specific website url and extracting its content.
    Input should be a valid url string.
    """
    # FirecrawlApp will automatically look for FIRECRAWL_API_KEY in env
    app = FirecrawlApp()
    
    try:
        scrape_result = app.scrape_url(url, params={'formats': ['markdown']})
        return scrape_result
    except Exception as e:
        return f"Error crawling {url}: {str(e)}"
