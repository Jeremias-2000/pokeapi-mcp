import logging

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context

from app.mcp.infra.tools.output_guard import guard_output
from app.mcp.infra.tools.pokemon import READ_ONLY
from app.mcp.infra.tools.request_context import request_meta

logger = logging.getLogger(__name__)


def register_health_tools(server: MCPServer) -> None:
    @server.tool(annotations=READ_ONLY)
    @guard_output
    async def health_check(ctx: Context) -> str:
        """Return the server health status."""
        logger.info("health_check called", extra=request_meta(ctx))
        return "ok"
