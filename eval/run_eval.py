"""
Evaluation runner for the credit memo agent.

Runs the agent against the evaluation dataset and applies all five evaluators.
By default, compares gpt-4.1-mini vs gpt-4.1 side-by-side in LangSmith.

Usage:
    python eval/run_eval.py                                    # Compare gpt-4.1-mini vs gpt-4.1
    python eval/run_eval.py --single-model gpt-4.1             # Single model only
    python eval/run_eval.py --models gpt-4.1-mini gpt-4.1     # Custom model list
    python eval/run_eval.py --experiment-prefix v2             # Custom experiment name
"""

import os
import sys
import uuid
import argparse

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENT_DIR = os.path.join(_PROJECT_ROOT, "agent")

# Add both project root (for eval.*) and agent/ (for tools.*, subagents.*, etc.)
sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, _AGENT_DIR)

from dotenv import load_dotenv
load_dotenv(override=True)

from langsmith import evaluate
from langgraph.store.memory import InMemoryStore

from eval.evaluators import (
    structural_quality,
    trajectory_quality,
    goal_achievement,
    regex_patterns,
    pe_credit_diligence,
)
from eval.dataset import DATASET_NAME

# Models to compare side-by-side in LangSmith
DEFAULT_MODELS = ["gpt-4.1-mini", "gpt-4.1"]


def create_agent(model: str = "gpt-4.1"):
    """Initialize the credit memo agent with all dependencies.

    Args:
        model: Model identifier for the orchestrator LLM.
    """
    # Seed the database
    db_path = os.path.join(_AGENT_DIR, "data", "deals.db")
    if not os.path.exists(db_path):
        from data.seed_db import main as seed_main
        seed_main()

    # Initialize RAG vector store
    from tools.rag_retriever import init_vector_store
    init_vector_store()

    # Create store with seeded memory
    store = InMemoryStore()
    store.put(
        ("analyst", "default"), "preferences",
        {"content": "Risk tolerance: Moderate. Preferred memo style: Concise, data-driven, lead with recommendation."}
    )
    store.put(
        ("market", "industrials"), "overview",
        {"content": "Industrials: Manufacturing PMI 51.2. Aerospace strong. Auto softening. Avg leverage 4.0-5.0x."}
    )
    store.put(
        ("market", "healthcare"), "overview",
        {"content": "Healthcare: Outpatient shift accelerating. CMS rates stable. Avg leverage 4.5-5.5x."}
    )
    store.put(
        ("market", "technology"), "overview",
        {"content": "Technology: Cloud/SaaS growth strong. Cybersecurity spending up. Avg leverage 3.5-4.5x."}
    )

    from deep_agent import create_orchestrator
    agent, _ = create_orchestrator(store=store, model=model)
    return agent


def make_run_function(agent):
    """Create a run function that captures both output and trajectory.

    The run function:
      1. Streams the agent with debug mode to capture tool calls
      2. Extracts the final response text
      3. Collects the tool call trajectory (name + args)
      4. Returns both for evaluators to inspect
    """
    def run_agent(inputs: dict) -> dict:
        request = inputs.get("request", "")
        config = {"configurable": {"thread_id": f"eval-{uuid.uuid4()}"}}

        trajectory = []
        final_output = ""

        # Stream with debug mode to capture tool calls including subagraph calls
        for namespace, chunk in agent.stream(
            {"messages": [{"role": "user", "content": request}]},
            config=config,
            stream_mode="debug",
            subgraphs=True,
        ):
            # Extract tool calls from debug events
            if isinstance(chunk, dict) and chunk.get("type") == "task":
                payload = chunk.get("payload", {})
                # Look for tool call inputs in the payload
                task_input = payload.get("input")
                task_name = payload.get("name", "")

                if task_name == "tools" and isinstance(task_input, list):
                    for tool_call in task_input:
                        if isinstance(tool_call, dict) and "name" in tool_call:
                            trajectory.append({
                                "tool": tool_call["name"],
                                "args": tool_call.get("args", {}),
                            })

        # Get the final state for the response text
        state = agent.get_state(config)
        messages = state.values.get("messages", [])
        if messages:
            last_msg = messages[-1]
            final_output = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        return {
            "output": final_output,
            "trajectory": trajectory,
        }

    return run_agent


ALL_EVALUATORS = [
    structural_quality,
    trajectory_quality,
    goal_achievement,
    regex_patterns,
    pe_credit_diligence,
]


def build_experiment_metadata(model: str) -> dict:
    """Build LangSmith experiment metadata to populate model/prompt/tool columns."""
    return {
        "models": [
            f"openai:{model}",
            {
                "id": ["langchain", "chat_models", "openai", "ChatOpenAI"],
                "lc": 1,
                "type": "constructor",
                "kwargs": {"model_name": model, "temperature": 0},
            },
        ],
        "prompts": ["credit-memo-orchestrator-system-prompt"],
        "tools": [
            {"name": "task", "description": "Delegate work to a specialized subagent"},
            {"name": "generate_memo_docx", "description": "Generate a formatted .docx credit memo"},
            {"name": "write_todos", "description": "Plan and track multi-step tasks"},
            {"name": "web_search", "description": "Search the web for borrower/sector info (Tavily)"},
            {"name": "rag_search", "description": "Semantic search over internal research docs"},
            {"name": "query_deals_db", "description": "SQL queries against the deal database"},
            {"name": "run_financial_calculation", "description": "Execute financial math in a sandbox"},
            {"name": "read_analyst_prefs", "description": "Read analyst preferences from memory"},
            {"name": "read_market_intel", "description": "Read sector intelligence from memory"},
            {"name": "save_market_intel", "description": "Save updated sector intelligence to memory"},
        ],
    }


def run_single_model(model: str, experiment_prefix: str):
    """Run the full eval suite for a single model configuration."""
    print(f"\n{'='*60}")
    print(f"  Model: {model}")
    print(f"  Experiment prefix: {experiment_prefix}")
    print(f"{'='*60}\n")

    agent = create_agent(model=model)
    run_fn = make_run_function(agent)

    results = evaluate(
        run_fn,
        data=DATASET_NAME,
        evaluators=ALL_EVALUATORS,
        experiment_prefix=experiment_prefix,
        description=f"Credit memo agent evaluation using {model} as the orchestrator model.",
        metadata=build_experiment_metadata(model),
        max_concurrency=1,  # Sequential to avoid thread/resource conflicts
    )

    print(f"\nCompleted: {experiment_prefix} ({model})")
    return results


def main():
    parser = argparse.ArgumentParser(description="Run credit memo agent evaluations")
    parser.add_argument(
        "--experiment-prefix",
        default="credit-memo",
        help="Prefix for the experiment name in LangSmith (default: credit-memo)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help=(
            "One or more model IDs to evaluate. If multiple are provided, "
            "each model gets its own experiment for side-by-side comparison. "
            f"Default: {' '.join(DEFAULT_MODELS)}"
        ),
    )
    parser.add_argument(
        "--single-model",
        default=None,
        help="Run evaluation with a single specific model (no comparison loop).",
    )
    args = parser.parse_args()

    print(f"Dataset: {DATASET_NAME}")
    print(f"Evaluators: {', '.join(e.__name__ for e in ALL_EVALUATORS)}")

    if args.single_model:
        # Run a single model only
        prefix = f"{args.experiment_prefix}-{args.single_model}"
        run_single_model(args.single_model, prefix)
    else:
        # Run the comparison loop across models
        models = args.models or DEFAULT_MODELS
        print(f"Comparing models: {', '.join(models)}")
        print("Each model will produce a separate experiment in LangSmith.")
        print("View them side-by-side on the dataset page.\n")

        for model in models:
            prefix = f"{args.experiment_prefix}-{model}"
            run_single_model(model, prefix)

    print("\n" + "="*60)
    print("All evaluations complete! View results in LangSmith:")
    print(f"  Project: credit-memo-agent")
    print(f"  Dataset: {DATASET_NAME}")
    print("  Compare experiments side-by-side on the dataset page.")


if __name__ == "__main__":
    main()
