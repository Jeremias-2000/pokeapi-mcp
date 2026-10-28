import logging

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context

from app.mcp.application.usecases.pokeapi_resources import PokeApiResourcesUseCase
from app.mcp.infra.tools.errors import translate_errors
from app.mcp.infra.tools.output_guard import guard_output
from app.mcp.infra.tools.pokemon import READ_ONLY
from app.mcp.infra.tools.request_context import request_meta
from app.mcp.infra.tools.schemas import Identifier, PageOffset, PageSize

logger = logging.getLogger(__name__)


def register_resource_tools(server: MCPServer, resources: PokeApiResourcesUseCase) -> None:
    @server.tool(title="Get type matchups", annotations=READ_ONLY, structured_output=True)
    @guard_output
    @translate_errors
    async def get_type_matchups(pokemon_type: Identifier, ctx: Context) -> dict[str, object]:
        """Return damage relations (double/half/no damage to and from) for a Pokémon type."""
        logger.info("get_type_matchups type=%s", pokemon_type, extra=request_meta(ctx))
        return await resources.type_matchups(pokemon_type)

    @server.tool(title="Get move details", annotations=READ_ONLY, structured_output=True)
    @guard_output
    @translate_errors
    async def get_move_details(move: Identifier, ctx: Context) -> dict[str, object]:
        """Return type, damage class, power, accuracy, PP and effect for a move."""
        logger.info("get_move_details move=%s", move, extra=request_meta(ctx))
        return await resources.move(move)

    @server.tool(title="Get ability details", annotations=READ_ONLY, structured_output=True)
    @guard_output
    @translate_errors
    async def get_ability_details(ability: Identifier, ctx: Context) -> dict[str, object]:
        """Return the effect of an ability and the Pokémon that can have it."""
        logger.info("get_ability_details ability=%s", ability, extra=request_meta(ctx))
        return await resources.ability(ability)

    @server.tool(title="Get item details", annotations=READ_ONLY, structured_output=True)
    @guard_output
    @translate_errors
    async def get_item_details(item: Identifier, ctx: Context) -> dict[str, object]:
        """Return category, cost, effect and sprite for an item."""
        logger.info("get_item_details item=%s", item, extra=request_meta(ctx))
        return await resources.item(item)

    @server.tool(title="List Pokémon", annotations=READ_ONLY, structured_output=True)
    @guard_output
    @translate_errors
    async def list_pokemon(ctx: Context, limit: PageSize = 20, offset: PageOffset = 0) -> dict[str, object]:
        """Return a paginated list of Pokémon names."""
        logger.info("list_pokemon limit=%s offset=%s", limit, offset, extra=request_meta(ctx))
        return await resources.list_resource("pokemon", limit, offset)

    @server.tool(title="List moves", annotations=READ_ONLY, structured_output=True)
    @guard_output
    @translate_errors
    async def list_moves(ctx: Context, limit: PageSize = 20, offset: PageOffset = 0) -> dict[str, object]:
        """Return a paginated list of move names."""
        logger.info("list_moves limit=%s offset=%s", limit, offset, extra=request_meta(ctx))
        return await resources.list_resource("move", limit, offset)

    @server.tool(title="List abilities", annotations=READ_ONLY, structured_output=True)
    @guard_output
    @translate_errors
    async def list_abilities(ctx: Context, limit: PageSize = 20, offset: PageOffset = 0) -> dict[str, object]:
        """Return a paginated list of ability names."""
        logger.info("list_abilities limit=%s offset=%s", limit, offset, extra=request_meta(ctx))
        return await resources.list_resource("ability", limit, offset)

    @server.tool(title="List items", annotations=READ_ONLY, structured_output=True)
    @guard_output
    @translate_errors
    async def list_items(ctx: Context, limit: PageSize = 20, offset: PageOffset = 0) -> dict[str, object]:
        """Return a paginated list of item names."""
        logger.info("list_items limit=%s offset=%s", limit, offset, extra=request_meta(ctx))
        return await resources.list_resource("item", limit, offset)
