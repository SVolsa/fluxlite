from ..i18n import _
from ..config import get as cfg_get

try:
    from tavily import TavilyClient
    HAS_TAVILY = True
except ImportError:
    HAS_TAVILY = False


def search(query: str, max_results: int = 5) -> str:
    if not HAS_TAVILY:
        return _("no_tavily_key") if _("no_tavily_key") else "[search] tavily-python not installed. Run: pip install tavily-python"

    api_key = cfg_get("tavily.key", "")

    try:
        client = TavilyClient(api_key=api_key)
        result = client.search(query=query, max_results=max_results)
    except Exception as e:
        return f"[search] Search error: {e}"

    if not result.get("results"):
        return f"[search] No results found for: {query}"

    lines = [f"[search] Results for: {query}", ""]
    for i, r in enumerate(result["results"], 1):
        title = r.get("title", "No title")
        url = r.get("url", "")
        content = r.get("content", "")
        lines.append(f"  {i}. {title}")
        lines.append(f"     {url}")
        if content:
            lines.append(f"     {content[:300]}...")
        lines.append("")

    return "\n".join(lines)
