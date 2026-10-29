"""Global output DLP: scan every tool result before it leaves the server.

Covers any tool registered without the per-tool ``guard_output`` decorator —
the decorators stay as defense in depth. Runs on ``tools/call`` results only,
scanning the serialized ``structuredContent`` (the typed payload the client
application consumes). Fail closed, same policy as the local guard: scanner
errors, BLOCK findings, and evasion reject the response; REDACT findings are
masked in place. Every outcome is audited on the ``guardrails.audit`` logger.
"""

import json
import logging
from typing import Any

from mcp import MCPError
from mcp.server.context import CallNext, HandlerResult, ServerRequestContext

from app.mcp.application.guardrails.dlp import redact, scan

logger = logging.getLogger("guardrails.audit")

OUTPUT_BLOCKED = -32043
_BLOCKED_MESSAGE = "[output_blocked] The response could not be delivered safely"


def _audit(decision: str, ctx: ServerRequestContext[Any, Any], **extra_details: object) -> None:
    details: dict[str, object] = {"stage": "output_dlp_global", "decision": decision, **extra_details}
    extra: dict[str, object] = {"details": details}
    if ctx.request_id is not None:
        extra["request_id"] = str(ctx.request_id)
    logger.info("guardrail decision", extra=extra)


def _structured(result: HandlerResult) -> dict[str, Any] | None:
    if isinstance(result, dict):
        value = result.get("structuredContent")
    else:
        value = getattr(result, "structured_content", None)
    return value if isinstance(value, dict) else None


async def guard_tool_outputs(ctx: ServerRequestContext[Any, Any], call_next: CallNext) -> HandlerResult:
    if ctx.method != "tools/call":
        return await call_next(ctx)
    result = await call_next(ctx)
    structured = _structured(result)
    if structured is None:
        return result
    try:
        serialized = json.dumps(structured, ensure_ascii=False)
    except (TypeError, ValueError):
        _audit("block", ctx, reason="serialization_error")
        raise MCPError(code=OUTPUT_BLOCKED, message=_BLOCKED_MESSAGE) from None
    try:
        outcome = scan(serialized)
    except Exception:  # fail closed: a DLP failure blocks the response
        _audit("block", ctx, reason="dlp_error")
        raise MCPError(code=OUTPUT_BLOCKED, message=_BLOCKED_MESSAGE) from None
    if outcome.blocked:
        _audit("block", ctx, reason="sensitive_data", findings=outcome.count_by_kind())
        raise MCPError(code=OUTPUT_BLOCKED, message=_BLOCKED_MESSAGE) from None
    if not outcome.findings:
        _audit("allow", ctx)
        return result
    masked = redact(serialized, outcome.findings)
    try:
        patched = json.loads(masked)
    except json.JSONDecodeError:  # marker replaced a numeric literal
        _audit("block", ctx, reason="redaction_error", findings=outcome.count_by_kind())
        raise MCPError(code=OUTPUT_BLOCKED, message=_BLOCKED_MESSAGE) from None
    _audit("redact", ctx, findings=outcome.count_by_kind())
    if isinstance(result, dict):
        return {**result, "structuredContent": patched}
    return result.model_copy(update={"structured_content": patched})
