"""Structured audit trail for guardrail decisions.

One entry per decision, correlated by request_id, recording the stage, the
decision (allow/deny/redact/block), and finding counts by kind. Sensitive
values are never logged — only types and counts.
"""

import logging

from mcp.server.mcpserver.context import Context

from app.mcp.infra.tools.request_context import request_meta

logger = logging.getLogger("guardrails.audit")


def audit_decision(
    *,
    stage: str,
    decision: str,
    tool: str,
    ctx: Context | None = None,
    reason: str | None = None,
    findings: dict[str, int] | None = None,
) -> None:
    details: dict[str, object] = {"stage": stage, "decision": decision, "tool": tool}
    if reason is not None:
        details["reason"] = reason
    if findings:
        details["findings"] = findings
    logger.info("guardrail decision", extra={**request_meta(ctx), "details": details})
