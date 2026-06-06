"""
Web Search Tool - Search the web using DuckDuckGo (free, no API key).
Requires: duckduckgo-search
"""

from typing import Optional


def search_web(query: str, max_results: int = 5, region: str = "wt-wt") -> str:
    """
    Search the web using DuckDuckGo.

    Args:
        query: Search query string
        max_results: Maximum number of results (1-20)
        region: Region code (e.g., 'wt-wt' for worldwide, 'cn-zh' for China)

    Returns:
        Formatted search results string
    """
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(
                ddgs.text(
                    query,
                    region=region,
                    safesearch="moderate",
                    max_results=min(max_results, 20),
                )
            )

        if not results:
            return f"No results found for: {query}"

        output = f"Search results for '{query}':\n\n"
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            href = r.get("href", "")
            body = r.get("body", "No description")
            output += f"{i}. {title}\n   URL: {href}\n   {body}\n\n"

        return output.strip()

    except ImportError:
        return "Install duckduckgo-search: pip install duckduckgo-search"
    except Exception as e:
        return f"Search error: {e}"


def search_news(query: str, max_results: int = 5) -> str:
    """Search for recent news articles."""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(
                ddgs.news(
                    keywords=query,
                    safesearch="moderate",
                    max_results=min(max_results, 10),
                )
            )

        if not results:
            return f"No news found for: {query}"

        output = f"News results for '{query}':\n\n"
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            url = r.get("url", "")
            source = r.get("source", "Unknown")
            date = r.get("date", "")
            body = r.get("body", "")
            output += (
                f"{i}. [{source}] {title}\n"
                f"   {date}\n"
                f"   {url}\n"
                f"   {body[:150]}...\n\n"
            )

        return output.strip()

    except ImportError:
        return "Install duckduckgo-search: pip install duckduckgo-search"
    except Exception as e:
        return f"News search error: {e}"


# Claude API tool definition
WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": (
        "Search the web for information. Use when the user asks about current events, "
        "facts you're unsure about, recent news, or anything requiring up-to-date "
        "information. Also use for 'look up', 'search for', 'find information about'. "
        "Do NOT use for local file searches."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query, e.g. 'Python 3.12 new features'",
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results (1-20, default 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}
