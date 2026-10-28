from app.mcp.application.guardrails.urls import allowlisted_url
from app.mcp.application.usecases.identifiers import normalize_identifier
from app.mcp.domain.exceptions import PokemonApiResponseError
from app.mcp.domain.interfaces.adapters.pokemon_api import PokemonApi


class GetPokemonDetailsUseCase:
    def __init__(self, pokemon_api: PokemonApi) -> None:
        self._pokemon_api = pokemon_api

    async def execute(self, pokemon: str) -> dict[str, object]:
        identifier = normalize_identifier(pokemon, "pokemon")
        data = await self._pokemon_api.get_resource("pokemon", identifier)
        try:
            return {
                "id": data["id"],
                "name": data["name"],
                "height": data["height"],
                "weight": data["weight"],
                "base_experience": data.get("base_experience"),
                "types": [t["type"]["name"] for t in data["types"]],
                "abilities": [
                    {"name": a["ability"]["name"], "is_hidden": a["is_hidden"]}
                    for a in data["abilities"]
                ],
                "stats": {s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
                "sprite": allowlisted_url(data["sprites"]["front_default"]),
            }
        except (KeyError, TypeError) as error:
            raise PokemonApiResponseError(
                "PokéAPI returned an invalid Pokémon payload"
            ) from error
