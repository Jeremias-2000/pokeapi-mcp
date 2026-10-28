from typing import Protocol, runtime_checkable


@runtime_checkable
class PokemonApi(Protocol):
    """Contract for the PokéAPI; implementations return raw JSON payloads."""

    async def get_resource(self, resource: str, identifier: str) -> dict[str, object]:
        ...

    async def list_resource(
        self, resource: str, limit: int, offset: int
    ) -> dict[str, object]:
        ...

    async def get_pokemon_encounters(self, identifier: str) -> list[dict[str, object]]:
        ...
