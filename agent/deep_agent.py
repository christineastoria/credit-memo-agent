"""
Credit Memo Orchestrator — Deep Agent Configuration

Creates and returns the credit memo orchestrator agent with all
subagents, tools, skills, middleware, and memory wiring.
"""

import os

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from subagents.research import research_subagent
from subagents.data import data_subagent
from subagents.calculations import calculations_subagent
from tools.memo_writer import generate_memo_docx
from tools.memory_tools import read_analyst_prefs, read_market_intel, save_market_intel
from middleware import ComplianceGuardrailMiddleware

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))


def create_orchestrator(store: InMemoryStore | None = None, model: str = "gpt-4.1"):
    """Create and return the credit memo orchestrator agent.

    Args:
        store: Optional InMemoryStore instance. If not provided, a new one
               is created. Pass an existing store to pre-seed memory.
        model: Model identifier for the orchestrator LLM (default: gpt-4.1).

    Returns:
        Tuple of (agent, store) — the compiled agent and its backing store.
    """
    if store is None:
        store = InMemoryStore()

    agent = create_deep_agent(
        name="credit-memo-orchestrator",
        model=model,

        system_prompt=(
            "You are a senior credit analyst orchestrator. Your job is to produce "
            "comprehensive credit investment memos by coordinating specialized subagents.\n\n"

            "WORKFLOW:\n"
            "1. Read analyst preferences using read_analyst_prefs\n"
            "2. Read sector intelligence using read_market_intel for the relevant sector\n"
            "3. Plan the memo using write_todos to track your progress\n"
            "4. Delegate research to the 'research' subagent — gather public and internal info\n"
            "5. Delegate data queries to the 'data' subagent — find comps and exposure\n"
            "6. Delegate calculations to the 'calculations' subagent — compute credit metrics\n"
            "7. Load the credit-memo-template skill for formatting guidance\n"
            "8. Synthesize all findings into the memo template sections\n"
            "9. Generate the .docx using generate_memo_docx with all required fields\n"
            "10. Save updated sector intelligence using save_market_intel\n\n"

            "IMPORTANT RULES:\n"
            "- Steps 4 and 5 can run in parallel — research and data are independent\n"
            "- Step 6 depends on both 4 and 5 — calculations need the gathered data\n"
            "- Always include the compliance disclaimer in the generated memo\n"
            "- Track all source citations from the research subagent\n"
            "- Be direct in recommendations — do not hedge excessively\n"
            "- If this borrower has been analyzed before, reference the prior analysis"
        ),

        tools=[generate_memo_docx, read_analyst_prefs, read_market_intel, save_market_intel],
        subagents=[research_subagent, data_subagent, calculations_subagent],
        backend=FilesystemBackend(root_dir=_AGENT_DIR, virtual_mode=True),
        skills=[os.path.join(_AGENT_DIR, "skills") + "/"],
        store=store,
        checkpointer=MemorySaver(),
        middleware=[ComplianceGuardrailMiddleware()],
    )

    return agent, store
