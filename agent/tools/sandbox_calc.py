"""
LangSmith sandbox tool for financial calculations.

Uses the LangSmith code sandbox to execute Python code remotely,
enabling the agent to perform complex financial calculations like
leverage ratios, coverage ratios, DCF models, and downside scenarios
without relying on LLM arithmetic.

Falls back to local exec() if LANGSMITH_API_KEY is not set.
"""

import os
import warnings

from langchain.tools import tool

_sandbox_available = False
if os.environ.get("LANGSMITH_API_KEY"):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            from langsmith.sandbox import SandboxClient
        _sandbox_available = True
    except ImportError:
        pass


def _run_local(code: str) -> str:
    """Execute code locally as a fallback when LangSmith sandbox is unavailable."""
    import io
    import contextlib
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(code, {"__builtins__": __builtins__}, {})
        output = buf.getvalue().strip()
        return output if output else "Code executed but produced no output."
    except Exception as e:
        return f"Calculation error: {e}"


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
    if not _sandbox_available:
        return _run_local(code)

    try:
        client = SandboxClient()
        with client.sandbox(name="credit-calc") as sandbox:
            result = sandbox.run(f"python3 -c \"{code}\"")
            output = result.stdout.strip()
            if result.stderr.strip():
                output += f"\nWarnings: {result.stderr.strip()}"
            return output if output else "Code executed but produced no output."

    except Exception as e:
        return f"Calculation error: {e}"
