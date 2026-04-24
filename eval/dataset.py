"""
Test dataset for credit memo agent evaluations.

Creates a LangSmith dataset with example inputs (borrower requests) and
reference outputs (expected sections, goals, trajectory patterns) that
the evaluators check against.

Usage:
    python eval/dataset.py              # Create and upload dataset
    python eval/dataset.py --local-only # Just print, don't upload
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(override=True)

from langsmith import Client

DATASET_NAME = "Credit Memo Agent Evals"
DATASET_DESCRIPTION = (
    "Evaluation dataset for the credit investment memo agent. "
    "Each example contains a borrower analysis request and reference outputs "
    "for structural, trajectory, goal, and regex evaluations."
)

# Each example has:
#   inputs: the user request sent to the agent
#   outputs: reference data for evaluators to check against
EXAMPLES = [
    {
        "inputs": {
            "request": (
                "Generate a credit memo for Acme Corp evaluating a new 300M dollar "
                "term loan opportunity. Use reasonable assumptions for missing data. "
                "Do not ask questions, just produce the memo."
            ),
            "borrower": "Acme Corp",
            "sector": "Industrials",
            "deal_type": "term_loan",
        },
        "outputs": {
            # --- For structural quality evaluator ---
            "required_sections": [
                "Executive Summary",
                "Business Overview",
                "Capital Structure",
                "Credit Metrics",
                "Industry Analysis",
                "Downside Scenarios",
                "Recommendation",
                "Sources & Citations",
            ],
            # --- For goal achievement evaluator (LLM judge) ---
            "goals": [
                "Provides a clear Buy/Pass/Monitor recommendation",
                "Includes specific leverage ratio (Debt/EBITDA) with a numeric value",
                "Includes interest coverage ratio with a numeric value",
                "Discusses downside scenarios with at least a base case and stress case",
                "References internal deal history or prior analysis for Acme Corp",
                "Mentions comparable deals from the same sector",
                "Identifies key risks specific to the borrower",
                "Includes a compliance disclaimer at the end",
                "Cites both external and internal sources",
                "Discusses the capital structure including existing debt instruments",
            ],
            # --- For trajectory evaluator (expected tool call patterns) ---
            "expected_tool_sequence": [
                "read_analyst_prefs",
                "read_market_intel",
                "write_todos",
                "task",  # research subagent
                "task",  # data subagent
                "task",  # calculations subagent
                "generate_memo_docx",
                "save_market_intel",
            ],
            "required_tools": [
                "task",
                "generate_memo_docx",
                "write_todos",
            ],
            # --- For regex pattern evaluator ---
            "expected_patterns": {
                "leverage_ratio": r"\d+\.\d+x",
                "percentage": r"\d+\.?\d*%",
                "dollar_amount": r"\$\d+[MB]?",
                "rating": r"B[B+-]?|CCC",
                "disclaimer_present": r"internal use only",
            },
            # --- For PE credit diligence evaluator ---
            "pe_diligence_criteria": [
                "Analyzes sponsor equity contribution and alignment of interests",
                "Provides downside protection analysis with recovery estimates under stress",
                "Assesses management team quality and key-person risk",
                "Evaluates covenant package quality (maintenance vs incurrence, headroom levels)",
                "Discusses exit or refinancing pathways and timeline",
                "Includes relative value comparison against comparable credits with spread analysis",
                "Addresses ESG risks or considerations relevant to the borrower",
            ],
        },
    },
    {
        "inputs": {
            "request": (
                "Generate a credit memo for Summit Healthcare Partners evaluating "
                "their existing credit profile and a potential 200M dollar direct "
                "lending facility. Do not ask questions, produce the memo."
            ),
            "borrower": "Summit Healthcare Partners",
            "sector": "Healthcare",
            "deal_type": "direct_lending",
        },
        "outputs": {
            "required_sections": [
                "Executive Summary",
                "Business Overview",
                "Capital Structure",
                "Credit Metrics",
                "Industry Analysis",
                "Downside Scenarios",
                "Recommendation",
                "Sources & Citations",
            ],
            "goals": [
                "Provides a clear Buy/Pass/Monitor recommendation",
                "Includes leverage ratio with a numeric value",
                "Discusses healthcare-specific risks (reimbursement, regulatory)",
                "References internal analysis history for Summit Healthcare",
                "Includes downside scenario analysis",
                "Mentions the outpatient surgery center business model",
                "Discusses geographic concentration risk",
                "Includes compliance disclaimer",
                "Cites both external and internal sources",
                "Analyzes the proposed 200M direct lending facility",
            ],
            "expected_tool_sequence": [
                "read_analyst_prefs",
                "read_market_intel",
                "write_todos",
                "task",
                "task",
                "task",
                "generate_memo_docx",
                "save_market_intel",
            ],
            "required_tools": [
                "task",
                "generate_memo_docx",
                "write_todos",
            ],
            "expected_patterns": {
                "leverage_ratio": r"\d+\.\d+x",
                "percentage": r"\d+\.?\d*%",
                "dollar_amount": r"\$\d+[MB]?",
                "rating": r"B[B+-]?|CCC",
                "disclaimer_present": r"internal use only",
            },
            "pe_diligence_criteria": [
                "Analyzes sponsor equity contribution and alignment of interests",
                "Provides downside protection analysis with recovery estimates under stress",
                "Assesses management team quality and key-person risk",
                "Evaluates covenant package quality (maintenance vs incurrence, headroom levels)",
                "Discusses exit or refinancing pathways and timeline",
                "Includes relative value comparison against comparable healthcare credits",
                "Addresses ESG risks specific to healthcare (patient safety, regulatory, data privacy)",
            ],
        },
    },
    {
        "inputs": {
            "request": (
                "Generate a credit memo for GlobalTech Industries evaluating "
                "their BB- rated leveraged loan. Do not ask questions, produce the memo."
            ),
            "borrower": "GlobalTech Industries",
            "sector": "Technology",
            "deal_type": "leveraged_loan",
        },
        "outputs": {
            "required_sections": [
                "Executive Summary",
                "Business Overview",
                "Capital Structure",
                "Credit Metrics",
                "Industry Analysis",
                "Downside Scenarios",
                "Recommendation",
                "Sources & Citations",
            ],
            "goals": [
                "Provides a clear Buy/Pass/Monitor recommendation",
                "Includes leverage ratio with a numeric value",
                "Discusses technology sector dynamics (SaaS, cybersecurity, etc.)",
                "References internal analysis for GlobalTech Industries",
                "Includes downside scenarios",
                "Mentions recurring revenue or ARR metrics",
                "Discusses acquisition integration risks",
                "Includes compliance disclaimer",
                "Cites sources",
                "Analyzes current capital structure",
            ],
            "expected_tool_sequence": [
                "read_analyst_prefs",
                "read_market_intel",
                "write_todos",
                "task",
                "task",
                "task",
                "generate_memo_docx",
                "save_market_intel",
            ],
            "required_tools": [
                "task",
                "generate_memo_docx",
                "write_todos",
            ],
            "expected_patterns": {
                "leverage_ratio": r"\d+\.\d+x",
                "percentage": r"\d+\.?\d*%",
                "dollar_amount": r"\$\d+[MB]?",
                "rating": r"B[B+-]?|CCC",
                "disclaimer_present": r"internal use only",
            },
            "pe_diligence_criteria": [
                "Analyzes sponsor equity contribution and alignment of interests",
                "Provides downside protection analysis with recovery estimates under stress",
                "Assesses management team quality and key-person risk",
                "Evaluates covenant package quality (maintenance vs incurrence, headroom levels)",
                "Discusses exit or refinancing pathways and timeline",
                "Includes relative value comparison against comparable technology credits",
                "Addresses ESG risks relevant to technology (data privacy, supply chain, energy use)",
            ],
        },
    },
]


def create_dataset(upload: bool = True):
    """Create the evaluation dataset, optionally uploading to LangSmith."""
    if upload:
        client = Client()

        # Delete existing dataset if it exists
        try:
            existing = client.read_dataset(dataset_name=DATASET_NAME)
            client.delete_dataset(dataset_id=existing.id)
            print(f"Deleted existing dataset: {DATASET_NAME}")
        except Exception:
            pass

        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description=DATASET_DESCRIPTION,
        )

        for i, example in enumerate(EXAMPLES):
            client.create_example(
                inputs=example["inputs"],
                outputs=example["outputs"],
                dataset_id=dataset.id,
                metadata={"borrower": example["inputs"]["borrower"], "index": i},
            )

        print(f"Uploaded dataset '{DATASET_NAME}' with {len(EXAMPLES)} examples to LangSmith.")
    else:
        print(json.dumps(EXAMPLES, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-only", action="store_true", help="Print dataset, don't upload")
    args = parser.parse_args()
    create_dataset(upload=not args.local_only)
