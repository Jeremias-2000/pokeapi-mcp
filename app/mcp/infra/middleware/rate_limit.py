"""Sliding-window rate limit for tool calls.

Refuses excess ``tools/call`` messages with an MCPError instead of running
the handler; the connection stays up and the next message goes through.
Caller key is the transport session id when present, else the client
address from the HTTP request, else a single shared bucket (stdio).

MCP defines no "busy" error code, so the server uses its own.
"""

import time
from collections import deque
from typing import Any

from mcp import MCPError
from mcp.server.context import CallNext, HandlerResult, ServerRequestContext

RATE_LIMITED = -32042


def _caller_key(ctx: ServerRequestContext[Any, Any]) -> str:
    session_id = getattr(ctx.session, "session_id", None)
    if session_id:
        return f"session:{session_id}"
    request = ctx.request
    client = getattr(request, "client", None)
    host = getattr(client, "host", None)
    if host:
        return f"client:{host}"
    return "shared"


def rate_limit(max_calls: int, window_seconds: float):
    """Allow at most ``max_calls`` tool calls per caller per sliding window."""
    calls: dict[str, deque[float]] = {}

    async def middleware(ctx: ServerRequestContext[Any, Any], call_next: CallNext) -> HandlerResult:
        if ctx.method != "tools/call":
            return await call_next(ctx)
        now = time.monotonic()
        key = _caller_key(ctx)
        bucket = calls.setdefault(key, deque())
        while bucket and now - bucket[0] >= window_seconds:
            bucket.popleft()
        if len(bucket) >= max_calls:
            raise MCPError(
                code=RATE_LIMITED,
                message=f"Rate limit exceeded: {max_calls} tool calls per {window_seconds:g}s",
            )
        bucket.append(now)
        return await call_next(ctx)

    return middleware
