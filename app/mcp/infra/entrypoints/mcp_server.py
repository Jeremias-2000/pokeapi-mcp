from mcp.server.mcpserver import MCPServer

from app.mcp.application.configuration.settings import get_settings
from app.mcp.application.usecases.get_pokemon_details import GetPokemonDetailsUseCase
from app.mcp.application.usecases.pokeapi_resources import PokeApiResourcesUseCase
from app.mcp.domain.interfaces.adapters.pokemon_api import PokemonApi
from app.mcp.infra.adapters.pokeapi_client import PokeApiClient
from app.mcp.infra.logging import load_logging_config
from app.mcp.infra.middleware.audit import audit_requests
from app.mcp.infra.middleware.output_guard import guard_tool_outputs
from app.mcp.infra.middleware.rate_limit import rate_limit
from app.mcp.infra.tools.registry import register_tools

load_logging_config()  # also runs in the uvicorn reload child process


def create_server() -> MCPServer:
    settings = get_settings()
    api: PokemonApi = PokeApiClient(settings)
    server = MCPServer(
        name="pokeapi-mcp",
        middleware=[
            # Outermost → innermost; audit wraps everything so duration
            # covers the full request including rate-limit and DLP checks.
            audit_requests,
            rate_limit(
                max_calls=settings.rate_limit_max_calls,
                window_seconds=settings.rate_limit_window_seconds,
            ),
            guard_tool_outputs,
        ],
    )
    register_tools(server, GetPokemonDetailsUseCase(api), PokeApiResourcesUseCase(api))
    return server


mcp = create_server()
app = mcp.streamable_http_app()
