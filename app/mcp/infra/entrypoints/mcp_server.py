from mcp.server.mcpserver import MCPServer

from app.mcp.application.configuration.settings import get_settings
from app.mcp.application.usecases.get_pokemon_details import GetPokemonDetailsUseCase
from app.mcp.application.usecases.pokeapi_resources import PokeApiResourcesUseCase
from app.mcp.domain.interfaces.adapters.pokemon_api import PokemonApi
from app.mcp.infra.adapters.pokeapi_client import PokeApiClient
from app.mcp.infra.logging import load_logging_config
from app.mcp.infra.tools.registry import register_tools

load_logging_config()  # also runs in the uvicorn reload child process


def create_server() -> MCPServer:
    api: PokemonApi = PokeApiClient(get_settings())
    server = MCPServer(name="pokeapi-mcp")
    register_tools(server, GetPokemonDetailsUseCase(api), PokeApiResourcesUseCase(api))
    return server


mcp = create_server()
app = mcp.streamable_http_app()
