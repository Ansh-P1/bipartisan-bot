import os

from agents.state import NewsItem


def _search_tavily(topic: str, max_results: int) -> list[NewsItem]:
    from tavily import TavilyClient

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY not set")

    client = TavilyClient(api_key=api_key)
    response = client.search(
        query=f"{topic} India policy news",
        max_results=max_results,
        topic="news",
    )

    results: list[NewsItem] = []
    for item in response.get("results", []):
        results.append(
            NewsItem(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                source="tavily",
            )
        )
    return results


def _search_ddg(topic: str, max_results: int) -> list[NewsItem]:
    from ddgs import DDGS

    query = f"{topic} India policy news"
    results: list[NewsItem] = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=max_results):
            results.append(
                NewsItem(
                    title=item.get("title", ""),
                    url=item.get("href", ""),
                    snippet=item.get("body", ""),
                    source="duckduckgo",
                )
            )
    return results


def search_news(topic: str, max_results: int = 6) -> list[NewsItem]:
    """Fetch news for a topic, preferring Tavily and falling back to DuckDuckGo.

    Tavily is purpose-built for agent retrieval (ranked, structured, date-filterable)
    but requires an API key. DDG needs no key so the app still works with zero
    search credentials configured — a deliberate reliability choice for live demos,
    not an accident.
    """
    try:
        results = _search_tavily(topic, max_results)
        if results:
            return results
    except Exception:
        pass

    try:
        return _search_ddg(topic, max_results)
    except Exception:
        return []


if __name__ == "__main__":
    import json

    news = search_news("data protection bill")
    print(json.dumps(news, indent=2))
