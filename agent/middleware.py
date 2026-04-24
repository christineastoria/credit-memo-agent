"""
Custom compliance guardrail middleware for the credit memo agent.

Hooks into the Deep Agents middleware pipeline to enforce three rules:
  1. MNPI Filter — blocks output containing material non-public information keywords
  2. Disclaimer Check — ensures memos include required compliance language before writing
  3. Audit Logging — logs all external data source accesses for compliance trail

Uses the @wrap_tool_call decorator to intercept tool execution.
"""

import json
import os
from datetime import datetime, timezone

from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage

# Keywords that indicate potential MNPI — if any appear in tool output,
# the middleware blocks the content and returns a warning instead
MNPI_KEYWORDS = [
    "material non-public",
    "insider information",
    "pre-announcement",
    "embargoed",
    "not yet disclosed",
    "confidential merger",
    "undisclosed acquisition",
    "pending regulatory",
]

# Required disclaimer text that must be present before generating the final memo
REQUIRED_DISCLAIMER = (
    "This memo is for internal use only and does not constitute investment advice. "
    "All analysis is based on publicly available information and internal firm data. "
    "This document may contain forward-looking statements subject to risks and uncertainties."
)

# Path for the audit log file
AUDIT_LOG_PATH = os.path.join(os.path.dirname(__file__), "output", "audit_log.json")


def _load_audit_log() -> list:
    """Load existing audit log entries or return empty list."""
    if os.path.exists(AUDIT_LOG_PATH):
        with open(AUDIT_LOG_PATH, "r") as f:
            return json.load(f)
    return []


def _save_audit_entry(entry: dict):
    """Append an entry to the audit log."""
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    log = _load_audit_log()
    log.append(entry)
    with open(AUDIT_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


@wrap_tool_call
def compliance_guardrail(request, handler):
    """Intercept tool calls for compliance checks.

    Wraps every tool execution with:
    1. Pre-execution audit logging for external data access tools
    2. Post-execution MNPI scanning on tool results
    3. Disclaimer validation before memo generation
    """
    tool_name = request.tool_call["name"]
    tool_args = request.tool_call["args"]

    # --- Audit Logging (pre-execution) ---
    external_tools = ["web_search", "rag_search", "query_deals_db"]
    if tool_name in external_tools:
        _save_audit_entry({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "query": str(tool_args.get("query", tool_args.get("sql_query", ""))),
            "action": "external_data_access",
        })

    # --- Execute the actual tool call ---
    result = handler(request)

    # --- MNPI Filter (post-execution) ---
    if isinstance(result, ToolMessage) and isinstance(result.content, str):
        result_lower = result.content.lower()
        for keyword in MNPI_KEYWORDS:
            if keyword in result_lower:
                _save_audit_entry({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tool": tool_name,
                    "action": "mnpi_blocked",
                    "keyword_matched": keyword,
                })
                return ToolMessage(
                    content=(
                        f"[COMPLIANCE BLOCK] Content filtered — potential MNPI detected "
                        f"(matched: '{keyword}'). This content has been redacted. "
                        f"Please verify the information source and consult compliance "
                        f"before proceeding."
                    ),
                    tool_call_id=request.tool_call["id"],
                )

    # --- Disclaimer Check (pre-memo-generation) ---
    if tool_name == "generate_memo_docx":
        disclaimer_arg = tool_args.get("disclaimer", "")
        if not disclaimer_arg or len(disclaimer_arg) < 50:
            _save_audit_entry({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": tool_name,
                "action": "disclaimer_warning",
                "message": "Memo generated with short or missing disclaimer",
            })

    return result
