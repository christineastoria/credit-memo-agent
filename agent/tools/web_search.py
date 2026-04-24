"""
Web search tool for internet research.

Currently uses Tavily for testing. To switch to Perplexity (which returns
richer citations), uncomment the Perplexity section and comment out Tavily.
"""

from langchain.tools import tool

# ============================================================
# OPTION A: Tavily (active — used for testing)
# ============================================================
from langchain_tavily import TavilySearch

# TavilySearch is a pre-built tool — we wrap it to add credit-specific
# context to the query and standardize the output format
_tavily = TavilySearch(
    max_results=5,
    topic="news",
    include_raw_content=False,
)


@tool
def web_search(query: str) -> str:
    """Search the internet for credit-relevant information about a company,
    industry, or financial topic. Returns findings with source citations.

    Use this for:
    - Company business overviews and recent news
    - Industry dynamics and competitive landscape
    - Public financial data and credit ratings
    - Regulatory or macroeconomic developments
    """
    # Add credit analysis context to get financially relevant results
    credit_query = (
        f"credit analysis investment memo: {query} "
        f"financial performance revenue EBITDA leverage debt"
    )

    # Invoke Tavily search
    result = _tavily.invoke(credit_query)
    return result


# ============================================================
# OPTION B: Perplexity (recommended for production — richer citations)
# Uncomment below and comment out Tavily above to switch.
# Requires PERPLEXITY_API_KEY in .env and langchain-perplexity installed.
# ============================================================
#
# from langchain_perplexity import ChatPerplexity
#
# perplexity_llm = ChatPerplexity(
#     model="sonar-pro",
#     temperature=0.0,
# )
#
# @tool
# def web_search(query: str) -> str:
#     """Search the internet for credit-relevant information about a company,
#     industry, or financial topic. Returns findings with source citations."""
#     credit_prompt = (
#         f"As a credit analyst researching for an investment memo, find detailed "
#         f"information about: {query}\n\n"
#         f"Focus on: business overview, financial performance, credit metrics, "
#         f"industry position, recent developments, and any risk factors. "
#         f"Include specific numbers and data points where available."
#     )
#     response = perplexity_llm.invoke(credit_prompt)
#     citations = response.response_metadata.get("citations", [])
#     output = response.content
#     if citations:
#         output += "\n\n--- SOURCES ---\n"
#         for i, citation in enumerate(citations, 1):
#             output += f"[{i}] {citation}\n"
#     return output
