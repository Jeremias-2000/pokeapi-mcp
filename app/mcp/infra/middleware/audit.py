"""One structured audit entry per inbound message.

Emits single-line JSON records on the ``guardrails.audit`` logger (the same
sink the guardrail decorators use), correlated by request_id. Method,
params size, duration, and outcome are recorded; params and result payloads
are never logged. The JSON formatter makes these lines directly shippable
to a SIEM.
"""

import logging
import time
from typing import Any

from mcp.server.context import CallNext, HandlerResult, ServerRequestContext

logger = logging.getLogger("guardrails.audit")


def _params_size(ctx: ServerRequestContext[Any, Any]) -> int | None:
    if ctx.params is None:
        return None
    return len(str(ctx.params))


async def audit_requests(ctx: ServerRequestContext[Any, Any], call_next: CallNext) -> HandlerResult:
    start = time.perf_counter()
    outcome = "ok"
    try:
        return await call_next(ctx)
    except Exception as error:
        outcome = type(error).__name__
        raise
    finally:
        details: dict[str, object] = {
            "stage": "request",
            "method": ctx.method,
            "outcome": outcome,
            "duration_ms": round((time.perf_counter() - start) * 1000, 1),
        }
        size = _params_size(ctx)
        if size is not None:
            details["params_bytes"] = size
        extra: dict[str, object] = {"details": details}
        if ctx.request_id is not None:
            extra["request_id"] = str(ctx.request_id)
        logger.info("mcp request", extra=extra)
