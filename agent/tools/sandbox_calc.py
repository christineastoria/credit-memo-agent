"""
LangSmith sandbox tool for financial calculations.

Uses the LangSmith code sandbox to execute Python code remotely,
enabling the agent to perform complex financial calculations like
leverage ratios, coverage ratios, DCF models, and downside scenarios
without relying on LLM arithmetic.
"""

import warnings

from langchain.tools import tool

# Suppress the alpha warning on import
with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    from langsmith.sandbox import SandboxClient


@tool
def run_financial_calculation(code: str) -> str:
    """Execute Python code in a secure sandbox for financial calculations.

    Use this for any computation that requires precise math:
    - Leverage ratios (Debt / EBITDA)
    - Interest coverage ratios (EBITDA / Interest Expense)
    - Free cash flow calculations
    - Debt paydown schedules
    - Downside scenario modeling (e.g., EBITDA decline impact)
    - Comparable deal analysis (averages, medians, spreads)

    The code should print() its results. Only standard Python libraries
    are available (math, statistics, etc.). No external packages.

    Example:
        debt = 950
        ebitda = 370
        interest = 97
        print(f"Leverage: {debt/ebitda:.1f}x")
        print(f"Coverage: {ebitda/interest:.1f}x")
    """
    try:
        # Create a sandbox client (uses LANGSMITH_API_KEY from env)
        client = SandboxClient()

        # Spin up a sandbox, run the code, and tear it down automatically
        with client.sandbox(name="credit-calc") as sandbox:
            result = sandbox.run(f"python3 -c \"{code}\"")
            output = result.stdout.strip()
            if result.stderr.strip():
                output += f"\nWarnings: {result.stderr.strip()}"
            return output if output else "Code executed but produced no output."

    except Exception as e:
        return f"Calculation error: {e}"
