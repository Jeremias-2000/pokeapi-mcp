import logging

from mcp.server.mcpserver import MCPServer

from app.mcp.application.usecases.get_pokemon_details import GetPokemonDetailsUseCase
from app.mcp.application.usecases.pokeapi_resources import PokeApiResourcesUseCase
from app.mcp.infra.tools.health import register_health_tools
from app.mcp.infra.tools.pokemon import register_pokemon_tools
from app.mcp.infra.tools.resources import register_resource_tools

logger = logging.getLogger(__name__)


def register_tools(
    server: MCPServer,
    details: GetPokemonDetailsUseCase,
    resources: PokeApiResourcesUseCase,
) -> None:
    register_health_tools(server)
    register_pokemon_tools(server, details, resources)
    register_resource_tools(server, resources)
    logger.info("MCP tools registered")
