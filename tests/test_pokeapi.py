import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.mcp.application.configuration.settings import Settings
from app.mcp.application.usecases.get_pokemon_details import GetPokemonDetailsUseCase
from app.mcp.application.usecases.pokeapi_resources import PokeApiResourcesUseCase
from app.mcp.domain.exceptions import (
    InvalidPokemonIdentifier,
    PokemonApiResponseError,
    PokemonApiUnavailable,
    PokemonNotFound,
)
from app.mcp.infra.adapters.pokeapi_client import PokeApiClient


class FakeApi:
    def __init__(self, resources: dict[str, dict], listing: dict | None = None) -> None:
        self.resources = resources
        self.listing = listing or {}
        self.calls: list[str] = []

    async def get_resource(self, resource: str, identifier: str) -> dict:
        self.calls.append(f"{resource}/{identifier}")
        return self.resources[f"{resource}/{identifier}"]

    async def list_resource(self, resource: str, limit: int, offset: int) -> dict:
        self.calls.append(f"list:{resource}:{limit}:{offset}")
        return self.listing

    async def get_pokemon_encounters(self, identifier: str) -> list[dict]:
        return [
            {
                "location_area": {"name": "route-1-area"},
                "version_details": [{"version": {"name": "red"}}],
            }
        ]


def named(name: str) -> dict:
    return {"name": name}


PIKACHU = {
    "id": 25,
    "name": "pikachu",
    "height": 4,
    "weight": 60,
    "base_experience": 112,
    "types": [{"type": named("electric")}],
    "abilities": [{"ability": named("static"), "is_hidden": False}],
    "stats": [{"stat": named("hp"), "base_stat": 35}],
    "sprites": {"front_default": "http://img"},
}


async def test_details_shapes_payload() -> None:
    result = await GetPokemonDetailsUseCase(FakeApi({"pokemon/pikachu": PIKACHU})).execute(" Pikachu ")
    assert result["types"] == ["electric"]
    assert result["stats"] == {"hp": 35}
    assert result["abilities"] == [{"name": "static", "is_hidden": False}]


async def test_details_rejects_bad_identifier() -> None:
    with pytest.raises(InvalidPokemonIdentifier):
        await GetPokemonDetailsUseCase(FakeApi({})).execute("../etc")


async def test_details_malformed_payload() -> None:
    with pytest.raises(PokemonApiResponseError):
        await GetPokemonDetailsUseCase(FakeApi({"pokemon/x": {"id": 1}})).execute("x")


async def test_evolution_flattens_chain() -> None:
    api = FakeApi(
        {
            "pokemon-species/pichu": {
                "id": 172,
                "name": "pichu",
                "color": named("yellow"),
                "habitat": None,
                "generation": named("generation-ii"),
                "is_legendary": False,
                "is_mythical": False,
                "genera": [{"language": named("en"), "genus": "Tiny Mouse"}],
                "flavor_text_entries": [],
                "evolution_chain": {"url": "https://pokeapi.co/api/v2/evolution-chain/10/"},
            },
            "evolution-chain/10": {
                "chain": {
                    "species": named("pichu"),
                    "evolves_to": [{"species": named("pikachu"), "evolves_to": []}],
                }
            },
        }
    )
    result = await PokeApiResourcesUseCase(api).evolution("pichu")
    assert result["chain"] == {
        "species": "pichu",
        "evolves_to": [{"species": "pikachu", "evolves_to": []}],
    }


async def test_list_validates_and_paginates() -> None:
    api = FakeApi(
        {},
        {
            "count": 100,
            "next": "https://pokeapi.co/api/v2/pokemon?offset=20&limit=20",
            "previous": None,
            "results": [{"name": "a", "url": "u"}],
        },
    )
    uc = PokeApiResourcesUseCase(api)
    result = await uc.list_resource("pokemon", 20, 0)
    assert result == {"count": 100, "next_offset": 20, "previous_offset": None, "results": [{"name": "a"}]}
    with pytest.raises(InvalidPokemonIdentifier):
        await uc.list_resource("pokemon", 0, 0)
    with pytest.raises(InvalidPokemonIdentifier):
        await uc.list_resource("pokemon", 10, -1)
    with pytest.raises(InvalidPokemonIdentifier):
        await uc.list_resource("berry", 10, 0)


async def test_move_uses_english_effect() -> None:
    api = FakeApi(
        {
            "move/tackle": {
                "id": 33,
                "name": "tackle",
                "type": named("normal"),
                "damage_class": named("physical"),
                "power": 40,
                "accuracy": 100,
                "pp": 35,
                "effect_entries": [
                    {"language": named("de"), "short_effect": "x"},
                    {"language": named("en"), "short_effect": "Inflicts damage."},
                ],
            }
        }
    )
    assert (await PokeApiResourcesUseCase(api).move("tackle"))["effect"] == (
        "<pokeapi_data>Inflicts damage.</pokeapi_data>"
    )


def client(handler) -> PokeApiClient:
    return PokeApiClient(Settings(), transport=httpx.MockTransport(handler))


async def test_client_success() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id": 1})

    assert await client(handler).get_resource("pokemon", "1") == {"id": 1}
    assert seen[0].url.path.endswith("/pokemon/1")


async def test_client_list_sends_params() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["limit"] == "5" and request.url.params["offset"] == "10"
        return httpx.Response(200, json={"results": []})

    await client(handler).list_resource("move", 5, 10)


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(404), PokemonNotFound),
        (httpx.Response(500), PokemonApiResponseError),
        (httpx.Response(200, content=b"not json"), PokemonApiResponseError),
        (httpx.Response(200, json=[1, 2]), PokemonApiResponseError),
    ],
)
async def test_client_errors(response: httpx.Response, error: type[Exception]) -> None:
    with pytest.raises(error):
        await client(lambda request: response).get_resource("pokemon", "x")


async def test_client_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(PokemonApiUnavailable):
        await client(handler).get_resource("pokemon", "x")
