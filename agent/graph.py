"""
LangGraph Studio entry point.

Exposes the compiled credit memo agent graph for visualization in Studio.
"""

import os
import sys

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AGENT_DIR)

from dotenv import load_dotenv
load_dotenv(override=True)

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from subagents.research import research_subagent
from subagents.data import data_subagent
from subagents.calculations import calculations_subagent
from tools.memo_writer import generate_memo_docx
from tools.memory_tools import read_analyst_prefs, read_market_intel, save_market_intel
from middleware import ComplianceGuardrailMiddleware
from data.seed_db import main as seed_main
from tools.rag_retriever import init_vector_store

# Seed database if needed
db_path = os.path.join(_AGENT_DIR, "data", "deals.db")
if not os.path.exists(db_path):
    seed_main()

init_vector_store()

graph = create_deep_agent(
    name="credit-memo-orchestrator",
    model="gpt-4.1",

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
    middleware=[ComplianceGuardrailMiddleware()],
)
