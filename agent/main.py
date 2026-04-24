"""
Credit Investment Memo Agent — Entry Point

Usage:
    python agent/main.py "Generate a credit memo for Acme Corp"
    python agent/main.py "Analyze Summit Healthcare Partners for a new $200M term loan"
    python agent/main.py  # interactive mode — prompts for input

This script:
  1. Loads environment variables (API keys)
  2. Seeds the SQLite database with dummy data (if not already present)
  3. Pre-seeds analyst preferences and market data into memory
  4. Creates the orchestrator Deep Agent with subagents, skills, and middleware
  5. Runs the agent with the user's request
"""

import os
import sys

# Add agent/ to sys.path so internal imports (tools.*, subagents.*, etc.) resolve
_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AGENT_DIR)

from dotenv import load_dotenv
load_dotenv(override=True)

from langgraph.store.memory import InMemoryStore

from deep_agent import create_orchestrator


def seed_database():
    """Ensure the SQLite database exists with dummy data."""
    db_path = os.path.join(_AGENT_DIR, "data", "deals.db")
    if not os.path.exists(db_path):
        print("Seeding database with dummy deal data...")
        from data.seed_db import main as seed_main
        seed_main()
    else:
        print("Database already exists, skipping seed.")


def seed_memory(store: InMemoryStore):
    """Pre-seed the Store with analyst preferences and market intelligence.

    This demonstrates how memory namespaces work:
      - ("analyst", <id>) stores per-analyst preferences
      - ("market", <sector>) stores sector-level intelligence
    """

    # Seed analyst preferences — the orchestrator reads these to tailor output
    store.put(
        ("analyst", "default"),
        "preferences",
        {
            "content": (
                "Risk tolerance: Moderate. "
                "Preferred memo style: Concise, data-driven, lead with recommendation. "
                "Focus areas: Downside protection, cash flow sustainability, covenant headroom. "
                "Sectors of interest: Healthcare, Technology, Industrials."
            )
        }
    )

    # Seed market intelligence for a couple sectors — these persist across memos
    store.put(
        ("market", "healthcare"),
        "overview",
        {
            "content": (
                "Healthcare sector outlook (as of Q4 2024): "
                "Outpatient shift continues to accelerate. CMS reimbursement rates stable for 2025. "
                "Labor costs remain elevated but stabilizing. M&A activity picking up in specialty care. "
                "Average leverage for healthcare credits: 4.5-5.5x. "
                "Typical spreads: L+475-600 for BB, L+600-750 for B-rated."
            )
        }
    )

    store.put(
        ("market", "industrials"),
        "overview",
        {
            "content": (
                "Industrials sector outlook (as of Q4 2024): "
                "Manufacturing PMI at 51.2 — modest expansion. Aerospace backlog strong (Boeing/Airbus). "
                "Automotive segment softening — OEM production cuts expected in H1 2025. "
                "Raw material costs (steel, aluminum) trending lower from 2023 peaks. "
                "Average leverage for industrial credits: 4.0-5.0x. "
                "Typical spreads: L+400-500 for BB, L+500-650 for B-rated."
            )
        }
    )

    print("Memory seeded with analyst preferences and market intelligence.")


def main():
    # Step 1: Seed the database
    seed_database()

    # Step 2: Create a Store and pre-seed memory
    store = InMemoryStore()
    seed_memory(store)

    # Step 3: Initialize the RAG vector store (must happen before agent runs in threads)
    from tools.rag_retriever import init_vector_store
    init_vector_store()

    # Step 4: Create the orchestrator agent
    print("Initializing credit memo orchestrator...")
    agent, store = create_orchestrator(store=store)

    # Step 5: Get the user's request
    if len(sys.argv) > 1:
        # Command-line argument mode
        user_request = " ".join(sys.argv[1:])
    else:
        # Interactive mode
        user_request = input("\nEnter your credit memo request:\n> ")

    print(f"\nProcessing: {user_request}\n")

    # Step 6: Run the agent
    config = {"configurable": {"thread_id": "memo-session-1"}}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_request}]},
        config=config,
    )

    # Step 7: Print the final response
    final_message = result["messages"][-1]
    print("\n" + "=" * 72)
    print("AGENT RESPONSE:")
    print("=" * 72)
    print(final_message.content)

    # Step 8: Show todo list progress if available
    todos = result.get("todos", [])
    if todos:
        print("\n" + "-" * 40)
        print("TASK PROGRESS:")
        for todo in todos:
            status_icon = {"completed": "done", "in_progress": "...", "pending": " "}.get(
                todo["status"], "?"
            )
            print(f"  [{status_icon}] {todo['content']}")


if __name__ == "__main__":
    main()
