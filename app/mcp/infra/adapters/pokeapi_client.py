import logging

import httpx

from app.mcp.application.configuration.settings import Settings
from app.mcp.domain.exceptions import (
    PokemonApiResponseError,
    PokemonApiUnavailable,
    PokemonNotFound,
)
from app.mcp.domain.interfaces.adapters.pokemon_api import PokemonApi

logger = logging.getLogger(__name__)


class PokeApiClient(PokemonApi):
    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = settings.pokeapi_base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=settings.pokeapi_timeout, transport=transport
        )

    async def get_resource(self, resource: str, identifier: str) -> dict[str, object]:
        data = await self._request(f"{resource}/{identifier}")
        if not isinstance(data, dict):
            raise PokemonApiResponseError("PokéAPI returned an invalid payload")
        return data

    async def list_resource(
        self, resource: str, limit: int, offset: int
    ) -> dict[str, object]:
        data = await self._request(
            resource, params={"limit": str(limit), "offset": str(offset)}
        )
        if not isinstance(data, dict):
            raise PokemonApiResponseError("PokéAPI returned an invalid payload")
        return data

    async def get_pokemon_encounters(self, identifier: str) -> list[dict[str, object]]:
        data = await self._request(f"pokemon/{identifier}/encounters")
        if not isinstance(data, list):
            raise PokemonApiResponseError("PokéAPI returned an invalid encounters payload")
        return data

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(
        self, path: str, params: dict[str, str] | None = None
    ) -> dict[str, object] | list[dict[str, object]]:
        try:
            response = await self._client.get(f"{self._base_url}/{path}", params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            if status == 404:
                logger.info("PokéAPI resource not found: %s", path)
                raise PokemonNotFound(
                    f"PokéAPI resource '{path}' was not found"
                ) from error
            logger.warning("PokéAPI returned HTTP %s for %s", status, path)
            raise PokemonApiResponseError(f"PokéAPI returned HTTP {status}") from error
        except httpx.RequestError as error:
            logger.warning("PokéAPI request failed for %s: %s", path, error)
            raise PokemonApiUnavailable("Could not connect to PokéAPI") from error

        try:
            data = response.json()
        except ValueError as error:
            raise PokemonApiResponseError("PokéAPI returned an invalid JSON payload") from error
        if not isinstance(data, (dict, list)):
            raise PokemonApiResponseError("PokéAPI returned an invalid payload")
        return data
