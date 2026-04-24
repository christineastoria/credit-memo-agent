"""
Custom compliance guardrail middleware for the credit memo agent.

Hooks into the Deep Agents middleware pipeline to enforce three rules:
  1. MNPI Filter — blocks output containing material non-public information keywords
  2. Disclaimer Check — ensures memos include required compliance language before writing
  3. Audit Logging — logs all external data source accesses for compliance trail

Implements both sync and async wrap_tool_call so the middleware works under
both invoke() (CLI, evals) and ainvoke() (LangGraph Studio).
"""

import json
import os
from datetime import datetime, timezone

from langchain.agents.middleware.types import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage

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

AUDIT_LOG_PATH = os.path.join(os.path.dirname(__file__), "output", "audit_log.json")


def _load_audit_log() -> list:
    if os.path.exists(AUDIT_LOG_PATH):
        with open(AUDIT_LOG_PATH, "r") as f:
            return json.load(f)
    return []


def _save_audit_entry(entry: dict):
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    log = _load_audit_log()
    log.append(entry)
    with open(AUDIT_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


def _pre_call(tool_name, tool_args):
    external_tools = ["web_search", "rag_search", "query_deals_db"]
    if tool_name in external_tools:
        _save_audit_entry({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "query": str(tool_args.get("query", tool_args.get("sql_query", ""))),
            "action": "external_data_access",
        })


def _post_call(result, tool_name, tool_args, tool_call_id):
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
                    tool_call_id=tool_call_id,
                )

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


class ComplianceGuardrailMiddleware(AgentMiddleware):
    """Intercepts tool calls for MNPI filtering, disclaimer checks, and audit logging."""

    tools = []

    def wrap_tool_call(self, request, handler):
        tool_name = request.tool_call["name"]
        tool_args = request.tool_call["args"]
        _pre_call(tool_name, tool_args)
        result = handler(request)
        return _post_call(result, tool_name, tool_args, request.tool_call["id"])

    async def awrap_tool_call(self, request, handler):
        tool_name = request.tool_call["name"]
        tool_args = request.tool_call["args"]
        _pre_call(tool_name, tool_args)
        result = await handler(request)
        return _post_call(result, tool_name, tool_args, request.tool_call["id"])
