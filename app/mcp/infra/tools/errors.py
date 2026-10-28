from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from mcp.server.mcpserver.exceptions import ToolError

from app.mcp.domain.exceptions import PokemonError
from app.mcp.infra.tools.audit import audit_decision
from app.mcp.infra.tools.request_context import find_context

P = ParamSpec("P")
R = TypeVar("R")


def translate_errors(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Expose domain errors (with their stable code) to MCP clients."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await func(*args, **kwargs)
        except PokemonError as error:
            audit_decision(
                stage="input", decision="deny", tool=func.__name__,
                ctx=find_context(args, kwargs), reason=error.code,
            )
            raise ToolError(str(error)) from error

    return wrapper
