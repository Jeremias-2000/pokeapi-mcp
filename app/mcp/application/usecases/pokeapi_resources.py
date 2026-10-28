from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.mcp.application.guardrails.text import sanitize_untrusted_text
from app.mcp.application.guardrails.urls import allowlisted_url
from app.mcp.application.usecases.identifiers import normalize_identifier
from app.mcp.domain.exceptions import InvalidPokemonIdentifier, PokemonApiResponseError
from app.mcp.domain.interfaces.adapters.pokemon_api import PokemonApi

LISTABLE = {"pokemon", "move", "ability", "item"}

# Output volume caps: nested collections are bounded before reaching the LLM.
MAX_ABILITY_POKEMON = 50
MAX_ENCOUNTERS = 100
MAX_CHAIN_DEPTH = 20


def _english(entries: list[dict[str, Any]], key: str) -> str | None:
    for entry in entries:
        if entry.get("language", {}).get("name") == "en":
            return entry.get(key)
    return None


def _guard(shape: Callable[..., dict[str, object]]) -> Callable[..., dict[str, object]]:
    def wrapper(*args: Any) -> dict[str, object]:
        try:
            return shape(*args)
        except (KeyError, TypeError, AttributeError) as error:
            raise PokemonApiResponseError("PokéAPI returned an unexpected payload") from error

    return wrapper


@_guard
def _species(data: dict[str, Any]) -> dict[str, object]:
    return {
        "id": data["id"],
        "name": data["name"],
        "color": data["color"]["name"],
        "habitat": (data.get("habitat") or {}).get("name"),
        "generation": data["generation"]["name"],
        "is_legendary": data["is_legendary"],
        "is_mythical": data["is_mythical"],
        "genus": sanitize_untrusted_text(_english(data["genera"], "genus")),
        "flavor_text": sanitize_untrusted_text(
            _english(data["flavor_text_entries"], "flavor_text")
        ),
        "evolution_chain_id": (data.get("evolution_chain") or {}).get("url", "")
        .rstrip("/")
        .rsplit("/", 1)[-1]
        or None,
    }


def _chain_node(node: dict[str, Any], depth: int = 0) -> dict[str, object]:
    if depth >= MAX_CHAIN_DEPTH:
        raise PokemonApiResponseError("PokéAPI evolution chain exceeds maximum depth")
    return {
        "species": node["species"]["name"],
        "evolves_to": [_chain_node(child, depth + 1) for child in node["evolves_to"]],
    }


@_guard
def _evolution(data: dict[str, Any]) -> dict[str, object]:
    return _chain_node(data["chain"])


@_guard
def _type(data: dict[str, Any]) -> dict[str, object]:
    return {
        "id": data["id"],
        "name": data["name"],
        "damage_relations": {
            relation: [t["name"] for t in types]
            for relation, types in data["damage_relations"].items()
        },
    }


@_guard
def _move(data: dict[str, Any]) -> dict[str, object]:
    return {
        "id": data["id"],
        "name": data["name"],
        "type": data["type"]["name"],
        "damage_class": data["damage_class"]["name"],
        "power": data.get("power"),
        "accuracy": data.get("accuracy"),
        "pp": data.get("pp"),
        "effect": sanitize_untrusted_text(_english(data.get("effect_entries", []), "short_effect")),
    }


@_guard
def _ability(data: dict[str, Any]) -> dict[str, object]:
    return {
        "id": data["id"],
        "name": data["name"],
        "effect": sanitize_untrusted_text(_english(data.get("effect_entries", []), "short_effect")),
        "pokemon": [p["pokemon"]["name"] for p in data["pokemon"]][:MAX_ABILITY_POKEMON],
    }


@_guard
def _item(data: dict[str, Any]) -> dict[str, object]:
    return {
        "id": data["id"],
        "name": data["name"],
        "category": data["category"]["name"],
        "cost": data["cost"],
        "effect": sanitize_untrusted_text(_english(data.get("effect_entries", []), "short_effect")),
        "sprite": allowlisted_url((data.get("sprites") or {}).get("default")),
    }


def _offset_of(url: object) -> int | None:
    if not isinstance(url, str):
        return None
    values = parse_qs(urlparse(url).query).get("offset")
    return int(values[0]) if values and values[0].isdigit() else None


class PokeApiResourcesUseCase:
    def __init__(self, pokemon_api: PokemonApi) -> None:
        self._api = pokemon_api

    async def species(self, pokemon: str) -> dict[str, object]:
        data = await self._api.get_resource(
            "pokemon-species", normalize_identifier(pokemon, "pokemon")
        )
        return _species(data)

    async def evolution(self, pokemon: str) -> dict[str, object]:
        species = await self.species(pokemon)
        chain_id = species["evolution_chain_id"]
        if not chain_id:
            return {"pokemon": species["name"], "chain": None}
        data = await self._api.get_resource("evolution-chain", str(chain_id))
        return {"pokemon": species["name"], "chain": _evolution(data)}

    async def encounters(self, pokemon: str) -> list[dict[str, object]]:
        raw = await self._api.get_pokemon_encounters(
            normalize_identifier(pokemon, "pokemon")
        )
        try:
            return [
                {
                    "location_area": item["location_area"]["name"],
                    "versions": [v["version"]["name"] for v in item["version_details"]],
                }
                for item in raw[:MAX_ENCOUNTERS]
            ]
        except (KeyError, TypeError) as error:
            raise PokemonApiResponseError("PokéAPI returned an unexpected payload") from error

    async def type_matchups(self, pokemon_type: str) -> dict[str, object]:
        return _type(
            await self._api.get_resource("type", normalize_identifier(pokemon_type, "type"))
        )

    async def move(self, move: str) -> dict[str, object]:
        return _move(await self._api.get_resource("move", normalize_identifier(move, "move")))

    async def ability(self, ability: str) -> dict[str, object]:
        return _ability(
            await self._api.get_resource("ability", normalize_identifier(ability, "ability"))
        )

    async def item(self, item: str) -> dict[str, object]:
        return _item(await self._api.get_resource("item", normalize_identifier(item, "item")))

    async def list_resource(
        self, resource: str, limit: int = 20, offset: int = 0
    ) -> dict[str, object]:
        if resource not in LISTABLE:
            raise InvalidPokemonIdentifier(f"resource must be one of {sorted(LISTABLE)}")
        if not 1 <= limit <= 100:
            raise InvalidPokemonIdentifier("limit must be between 1 and 100")
        if offset < 0:
            raise InvalidPokemonIdentifier("offset must be zero or greater")
        data = await self._api.list_resource(resource, limit, offset)
        try:
            return {
                "count": data["count"],
                "next_offset": _offset_of(data.get("next")),
                "previous_offset": _offset_of(data.get("previous")),
                "results": [{"name": r["name"]} for r in data["results"]],  # type: ignore[index]
            }
        except (KeyError, TypeError) as error:
            raise PokemonApiResponseError("PokéAPI returned an unexpected payload") from error
