"""Helpers for decorators that need the request context of a tool call."""

from mcp.server.mcpserver.context import Context

from app.mcp.infra.tools.identity import identity_from_context


def find_context(args: tuple[object, ...], kwargs: dict[str, object]) -> Context | None:
    for value in (*args, *kwargs.values()):
        if isinstance(value, Context):
            return value
    return None


def request_meta(ctx: Context | None) -> dict[str, str]:
    """Logging/audit extras for a request: correlation id and identity."""
    meta: dict[str, str] = {}
    if ctx is not None:
        try:
            meta["request_id"] = ctx.request_id
        except ValueError:
            pass
    meta["sub"] = identity_from_context(ctx).sub
    return meta
