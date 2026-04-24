"""
Memory tools for accessing persistent Store-backed data.

These tools give the orchestrator access to two namespaced memory areas:
  - ("analyst", <analyst_id>): Analyst preferences and style
  - ("market", <sector>): Sector intelligence that persists across memos

Uses ToolRuntime to access the Store instance passed to create_deep_agent.
"""

from langchain.tools import tool, ToolRuntime


@tool
def read_analyst_prefs(analyst_id: str, runtime: ToolRuntime) -> str:
    """Read analyst preferences from persistent memory.

    Returns the analyst's preferred memo style, risk tolerance framing,
    and focus areas. Use 'default' as analyst_id if not specified.
    """
    store = runtime.store
    if store is None:
        return "No memory store configured."

    result = store.get(("analyst", analyst_id), "preferences")
    if result and result.value:
        # The value is stored via create_file_data, extract the content
        value = result.value
        if isinstance(value, dict) and "content" in value:
            return value["content"]
        return str(value)
    return f"No preferences found for analyst '{analyst_id}'."


@tool
def read_market_intel(sector: str, runtime: ToolRuntime) -> str:
    """Read sector intelligence from persistent memory.

    Returns market trends, typical metrics, and competitive dynamics
    for the given sector (e.g., 'healthcare', 'industrials', 'technology').
    """
    store = runtime.store
    if store is None:
        return "No memory store configured."

    result = store.get(("market", sector.lower()), "overview")
    if result and result.value:
        value = result.value
        if isinstance(value, dict) and "content" in value:
            return value["content"]
        return str(value)
    return f"No market intelligence found for sector '{sector}'."


@tool
def save_market_intel(sector: str, intelligence: str, runtime: ToolRuntime) -> str:
    """Save updated sector intelligence to persistent memory.

    Call this after completing a memo to store any new sector insights
    that should inform future memos for the same sector.
    """
    store = runtime.store
    if store is None:
        return "No memory store configured."

    store.put(
        ("market", sector.lower()),
        "overview",
        {"content": intelligence}
    )
    return f"Market intelligence for '{sector}' saved to persistent memory."
