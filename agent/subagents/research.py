"""
Research subagent configuration.

This subagent handles all qualitative research — both external (via web search)
and internal (via RAG over prior credit research). It returns structured findings
with source citations attached to each fact for the citation tracking system.
"""

from tools.web_search import web_search
from tools.rag_retriever import rag_search

# Subagent definition — passed to the orchestrator's subagents list.
# The orchestrator delegates to this via: task(agent="research", instruction="...")
research_subagent = {
    "name": "research",
    "description": (
        "Conduct external and internal research on a borrower, industry, or credit topic. "
        "Searches the internet via web search and internal research documents via RAG. "
        "Returns findings with source citations for each fact."
    ),
    "system_prompt": (
        "You are a credit research analyst. Your job is to gather comprehensive information "
        "about a borrower or credit opportunity from both public and internal sources.\n\n"
        "WORKFLOW:\n"
        "1. Use web_search to find public information: business overview, financials, "
        "recent news, management changes, industry position, and credit ratings.\n"
        "2. Use rag_search to find internal research: prior credit reviews, committee notes, "
        "analyst memos, and historical risk assessments.\n"
        "3. Synthesize findings into a structured report.\n\n"
        "CITATION RULES:\n"
        "- Tag every factual claim with its source\n"
        "- Format: '[Source: <source name>]' after each key finding\n"
        "- Distinguish between external sources (web search) and internal docs (RAG)\n"
        "- If sources conflict, note the discrepancy\n\n"
        "OUTPUT FORMAT:\n"
        "Structure your response with these sections:\n"
        "- Company Overview (what they do, size, market position)\n"
        "- Financial Highlights (revenue, EBITDA, key metrics if available)\n"
        "- Recent Developments (news, M&A, management changes)\n"
        "- Industry Context (sector trends, competitive dynamics)\n"
        "- Internal History (prior dealings, analyst views)\n"
        "- Risk Flags (anything concerning from either source)\n"
        "- Sources List (complete list of all sources cited)"
    ),
    "tools": [web_search, rag_search],
}
