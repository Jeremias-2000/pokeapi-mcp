import logging

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.types import ToolAnnotations

from app.mcp.application.usecases.get_pokemon_details import GetPokemonDetailsUseCase
from app.mcp.application.usecases.pokeapi_resources import PokeApiResourcesUseCase
from app.mcp.infra.tools.errors import translate_errors
from app.mcp.infra.tools.output_guard import guard_output
from app.mcp.infra.tools.request_context import request_meta
from app.mcp.infra.tools.schemas import Identifier

logger = logging.getLogger(__name__)

READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


def register_pokemon_tools(
    server: MCPServer,
    details: GetPokemonDetailsUseCase,
    resources: PokeApiResourcesUseCase,
) -> None:
    @server.tool(title="Get Pokémon details", annotations=READ_ONLY, structured_output=True)
    @guard_output
    @translate_errors
    async def get_pokemon_details(pokemon: Identifier, ctx: Context) -> dict[str, object]:
        """Return types, abilities, base stats and sprite for a Pokémon (name or Pokédex ID)."""
        logger.info("get_pokemon_details pokemon=%s", pokemon, extra=request_meta(ctx))
        return await details.execute(pokemon)

    @server.tool(title="Get Pokémon species", annotations=READ_ONLY, structured_output=True)
    @guard_output
    @translate_errors
    async def get_pokemon_species(pokemon: Identifier, ctx: Context) -> dict[str, object]:
        """Return species data: color, habitat, generation, legendary flags, genus, flavor text."""
        logger.info("get_pokemon_species pokemon=%s", pokemon, extra=request_meta(ctx))
        return await resources.species(pokemon)

    @server.tool(title="Get Pokémon evolution", annotations=READ_ONLY, structured_output=True)
    @guard_output
    @translate_errors
    async def get_pokemon_evolution(pokemon: Identifier, ctx: Context) -> dict[str, object]:
        """Return the nested evolution chain a Pokémon belongs to."""
        logger.info("get_pokemon_evolution pokemon=%s", pokemon, extra=request_meta(ctx))
        return await resources.evolution(pokemon)

    @server.tool(title="Get Pokémon encounters", annotations=READ_ONLY, structured_output=True)
    @guard_output
    @translate_errors
    async def get_pokemon_encounters(pokemon: Identifier, ctx: Context) -> list[dict[str, object]]:
        """Return location areas and game versions where a Pokémon can be encountered."""
        logger.info("get_pokemon_encounters pokemon=%s", pokemon, extra=request_meta(ctx))
        return await resources.encounters(pokemon)
