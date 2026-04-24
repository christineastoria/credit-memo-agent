"""
Evaluation suite for the credit memo agent.

Five evaluator types:
  1. structural_quality   — code check: verifies required memo sections are present
  2. trajectory_quality   — LLM judge: evaluates tool call sequence and argument quality
  3. goal_achievement     — LLM judge: checks if memo achieves goals from reference
  4. regex_patterns       — code check: validates formatting patterns (ratios, $, disclaimers)
  5. pe_credit_diligence  — LLM judge: PE credit fund diligence criteria

Each evaluator returns {"score": float, "comment": str} as required by LangSmith.
The metric key is auto-derived from the function name.
"""

import re
from typing import TypedDict, Annotated

from langchain_openai import ChatOpenAI

# ---------------------------------------------------------------------------
# Helper to safely extract outputs from run/example (handles both RunTree and dict)
# ---------------------------------------------------------------------------

def _get_outputs(obj):
    return obj.outputs if hasattr(obj, "outputs") else obj.get("outputs", {}) or {}


def _get_inputs(obj):
    return obj.inputs if hasattr(obj, "inputs") else obj.get("inputs", {}) or {}


def _safe_output_text(run_outputs: dict) -> str:
    """Extract output text from run outputs, handling None and dict values."""
    text = run_outputs.get("output") or ""
    if isinstance(text, dict):
        text = str(text)
    return text


# ===========================================================================
# 1. STRUCTURAL QUALITY (code evaluator)
#    Checks that the agent's final response contains all required memo sections.
# ===========================================================================

def structural_quality(run, example) -> dict:
    """Check that all required memo sections appear in the agent output.

    Scores 1.0 if all sections present, proportional score otherwise.
    """
    run_outputs = _get_outputs(run)
    example_outputs = _get_outputs(example)

    output_text = _safe_output_text(run_outputs)
    required_sections = example_outputs.get("required_sections", [])

    if not required_sections:
        return {"score": 1.0, "comment": "No required sections defined."}

    output_lower = output_text.lower()
    found = []
    missing = []
    for section in required_sections:
        if section.lower() in output_lower:
            found.append(section)
        else:
            missing.append(section)

    score = len(found) / len(required_sections)

    if missing:
        comment = f"Missing sections: {', '.join(missing)}. Found {len(found)}/{len(required_sections)}."
    else:
        comment = f"All {len(required_sections)} required sections present."

    return {"score": score, "comment": comment}


# ===========================================================================
# 2. TRAJECTORY QUALITY (LLM judge)
#    Evaluates the tool call sequence: are the right tools called in a
#    sensible order with valid arguments?
# ===========================================================================

class TrajectoryGrade(TypedDict):
    reasoning: Annotated[str, ..., "Step-by-step reasoning about trajectory quality"]
    tool_selection_score: Annotated[int, ..., "1-5: Were the right tools selected?"]
    argument_quality_score: Annotated[int, ..., "1-5: Were tool arguments well-formed and specific?"]
    efficiency_score: Annotated[int, ..., "1-5: Was the trajectory efficient (no redundant calls)?"]
    overall_score: Annotated[int, ..., "1-5: Overall trajectory quality"]

_trajectory_judge = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
).with_structured_output(TrajectoryGrade, method="json_schema", strict=True)


async def trajectory_quality(run, example) -> dict:
    """LLM judge that evaluates the tool call trajectory for quality.

    Checks tool selection, argument validity, and execution efficiency.
    Returns a normalized 0-1 score.
    """
    run_outputs = _get_outputs(run)
    example_outputs = _get_outputs(example)

    trajectory = run_outputs.get("trajectory", [])
    expected_tools = example_outputs.get("required_tools", [])

    traj_description = ""
    for i, call in enumerate(trajectory, 1):
        tool_name = call.get("tool", "unknown")
        args_summary = str(call.get("args", {}))[:200]
        traj_description += f"{i}. {tool_name}({args_summary})\n"

    if not traj_description:
        traj_description = "No tool calls captured in trajectory."

    prompt = f"""You are evaluating the tool call trajectory of a credit memo agent.

The agent was asked to generate a credit investment memo. Below is the sequence of tool calls it made.

EXPECTED TOOLS (must appear at least once): {', '.join(expected_tools)}

ACTUAL TRAJECTORY:
{traj_description}

Evaluate on these criteria:
1. Tool Selection (1-5): Did the agent use the right tools? Did it call research, data, calculations, and memo generation?
2. Argument Quality (1-5): Were tool arguments specific and well-formed? Did subagent task instructions contain enough context?
3. Efficiency (1-5): Was the trajectory efficient? Were there redundant or unnecessary calls?
4. Overall (1-5): Holistic trajectory quality.

Score generously: 3 = acceptable with minor gaps, 4 = good (expected for a working agent), 5 = excellent."""

    grade = await _trajectory_judge.ainvoke([{"role": "user", "content": prompt}])

    score = grade["overall_score"] / 5.0

    return {
        "score": score,
        "comment": (
            f"Tool selection: {grade['tool_selection_score']}/5, "
            f"Arg quality: {grade['argument_quality_score']}/5, "
            f"Efficiency: {grade['efficiency_score']}/5, "
            f"Overall: {grade['overall_score']}/5. "
            f"Reasoning: {grade['reasoning']}"
        ),
    }


# ===========================================================================
# 3. GOAL ACHIEVEMENT (LLM judge)
#    Checks if the memo achieves a list of specific goals from the reference.
# ===========================================================================

class GoalGrade(TypedDict):
    reasoning: Annotated[str, ..., "Assessment of which goals were met and why"]
    goals_met: Annotated[list[str], ..., "List of goals that were achieved"]
    goals_missed: Annotated[list[str], ..., "List of goals that were NOT achieved"]
    score: Annotated[int, ..., "Number of goals achieved out of total"]

_goal_judge = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
).with_structured_output(GoalGrade, method="json_schema", strict=True)


async def goal_achievement(run, example) -> dict:
    """LLM judge that checks whether the memo achieves specific goals.

    Each dataset example defines a list of goals the memo should satisfy.
    Returns a proportional score (goals met / total goals).
    """
    run_outputs = _get_outputs(run)
    example_outputs = _get_outputs(example)
    example_inputs = _get_inputs(example)

    output_text = _safe_output_text(run_outputs)
    goals = example_outputs.get("goals", [])
    borrower = example_inputs.get("borrower", "Unknown")

    if not goals:
        return {"score": 1.0, "comment": "No goals defined."}

    goals_list = "\n".join(f"{i+1}. {g}" for i, g in enumerate(goals))

    prompt = f"""You are evaluating a credit investment memo for {borrower}.

MEMO CONTENT:
{output_text[:8000]}

GOALS TO CHECK (the memo should achieve ALL of these):
{goals_list}

For each goal, determine if the memo addresses it. A goal is "met" if the memo contains
relevant content on that topic — it does not need to be exhaustive, just clearly present.
Give credit for reasonable coverage even if the analysis could be deeper.

Each goal is either met or missed. Be fair and give the benefit of the doubt."""

    grade = await _goal_judge.ainvoke([{"role": "user", "content": prompt}])

    total = len(goals)
    met = len(grade["goals_met"])
    score = met / total if total > 0 else 1.0

    missed_str = ", ".join(grade["goals_missed"]) if grade["goals_missed"] else "none"

    return {
        "score": score,
        "comment": (
            f"{met}/{total} goals achieved. "
            f"Missed: {missed_str}. "
            f"Reasoning: {grade['reasoning']}"
        ),
    }


# ===========================================================================
# 4. REGEX PATTERNS (code evaluator)
#    Validates that the memo output contains expected formatting patterns
#    like leverage ratios (4.7x), percentages (20.0%), dollar amounts ($300M),
#    credit ratings (BB-), and compliance disclaimer text.
# ===========================================================================

def regex_patterns(run, example) -> dict:
    """Check that the agent output matches expected regex patterns.

    Each pattern represents a formatting convention for credit memos:
    leverage ratios, percentages, dollar amounts, ratings, and disclaimers.
    """
    run_outputs = _get_outputs(run)
    example_outputs = _get_outputs(example)

    output_text = _safe_output_text(run_outputs)
    patterns = example_outputs.get("expected_patterns", {})

    if not patterns:
        return {"score": 1.0, "comment": "No patterns defined."}

    output_lower = output_text.lower()
    results = {}
    matched = 0

    for name, pattern in patterns.items():
        if name == "disclaimer_present":
            found = bool(re.search(pattern, output_lower))
        else:
            found = bool(re.search(pattern, output_text))

        results[name] = found
        if found:
            matched += 1

    score = matched / len(patterns)

    details = []
    for name, found in results.items():
        status = "PASS" if found else "FAIL"
        details.append(f"{name}: {status}")

    return {
        "score": score,
        "comment": f"{matched}/{len(patterns)} patterns matched. {'; '.join(details)}",
    }


# ===========================================================================
# 5. PE CREDIT DILIGENCE (LLM judge)
#    Evaluates the memo against private equity credit diligence criteria:
#    sponsor economics, downside protection, covenant analysis, key-person
#    risk, and exit pathways.
# ===========================================================================

class PEDiligenceGrade(TypedDict):
    reasoning: Annotated[str, ..., "Detailed assessment of PE diligence quality"]
    criteria_met: Annotated[list[str], ..., "List of PE criteria adequately addressed"]
    criteria_missed: Annotated[list[str], ..., "List of PE criteria NOT addressed"]
    score: Annotated[int, ..., "Number of criteria met out of total"]

_pe_judge = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
).with_structured_output(PEDiligenceGrade, method="json_schema", strict=True)


async def pe_credit_diligence(run, example) -> dict:
    """LLM judge applying PE credit diligence standards.

    Checks whether the memo addresses the deeper due diligence questions
    a private equity credit fund would ask before committing capital:
    sponsor alignment, downside/recovery, management risk, covenant
    quality, exit paths, relative value, and ESG.
    """
    run_outputs = _get_outputs(run)
    example_outputs = _get_outputs(example)
    example_inputs = _get_inputs(example)

    output_text = _safe_output_text(run_outputs)
    pe_criteria = example_outputs.get("pe_diligence_criteria", [])
    borrower = example_inputs.get("borrower", "Unknown")

    if not pe_criteria:
        return {"score": 1.0, "comment": "No PE diligence criteria defined."}

    criteria_list = "\n".join(f"{i+1}. {c}" for i, c in enumerate(pe_criteria))

    prompt = f"""You are a credit analyst reviewing a credit investment memo for {borrower}.

Evaluate whether this memo addresses each PE diligence criterion below.
A criterion is "met" if the memo discusses the topic with relevant detail — it does not
need to be exhaustive, but the topic should be clearly covered rather than completely absent.

MEMO CONTENT:
{output_text[:8000]}

PE CREDIT DILIGENCE CRITERIA:
{criteria_list}

For each criterion, determine if the memo provides reasonable coverage.
Give credit for relevant discussion even if the depth could be greater.
Each criterion is either met or missed."""

    grade = await _pe_judge.ainvoke([{"role": "user", "content": prompt}])

    total = len(pe_criteria)
    met = len(grade["criteria_met"])
    score = met / total if total > 0 else 1.0

    missed_str = ", ".join(grade["criteria_missed"]) if grade["criteria_missed"] else "none"

    return {
        "score": score,
        "comment": (
            f"PE diligence: {met}/{total} criteria met. "
            f"Missed: {missed_str}. "
            f"Reasoning: {grade['reasoning']}"
        ),
    }
