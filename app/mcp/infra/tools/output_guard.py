"""Stage 5 output guard: DLP over the serialized DTO plus decision auditing.

Runs after the use case has shaped its allowlisted DTO and before the result
leaves the server. Fail closed: a scanner error, a BLOCK-severity finding, or
evasion detected after normalization rejects the response with an opaque
error; REDACT findings are masked in place. Every outcome is audited.
"""

import json
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from mcp.server.mcpserver.exceptions import ToolError

from app.mcp.application.guardrails.dlp import redact, scan
from app.mcp.infra.tools.audit import audit_decision
from app.mcp.infra.tools.request_context import find_context

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)

_BLOCKED_ERROR = "[output_blocked] The response could not be delivered safely"


def guard_output(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        result = await func(*args, **kwargs)
        ctx = find_context(args, kwargs)
        try:
            serialized = json.dumps(result, ensure_ascii=False)
        except (TypeError, ValueError):  # non-serializable result: a code bug, not DLP
            logger.exception("Tool result is not JSON-serializable")
            audit_decision(
                stage="output_dlp", decision="block", tool=func.__name__,
                ctx=ctx, reason="serialization_error",
            )
            raise ToolError(_BLOCKED_ERROR) from None
        try:
            outcome = scan(serialized)
        except Exception:  # fail closed: a DLP failure blocks the response
            logger.exception("DLP scan failed")
            audit_decision(
                stage="output_dlp", decision="block", tool=func.__name__,
                ctx=ctx, reason="dlp_error",
            )
            raise ToolError(_BLOCKED_ERROR) from None
        if outcome.blocked:
            audit_decision(
                stage="output_dlp", decision="block", tool=func.__name__,
                ctx=ctx, reason="sensitive_data",
                findings=outcome.count_by_kind(),
            )
            raise ToolError(_BLOCKED_ERROR) from None
        if outcome.findings:
            serialized = redact(serialized, outcome.findings)
            try:
                result = json.loads(serialized)
            except json.JSONDecodeError:  # marker replaced a numeric literal
                logger.error("Redaction produced invalid JSON")
                audit_decision(
                    stage="output_dlp", decision="block", tool=func.__name__,
                    ctx=ctx, reason="redaction_error",
                    findings=outcome.count_by_kind(),
                )
                raise ToolError(_BLOCKED_ERROR) from None
        audit_decision(
            stage="output_dlp",
            decision="redact" if outcome.findings else "allow",
            tool=func.__name__, ctx=ctx,
            findings=outcome.count_by_kind() or None,
        )
        return result

    return wrapper
