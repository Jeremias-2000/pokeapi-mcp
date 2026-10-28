class PokemonError(Exception):
    """Base exception for expected Pokémon use-case failures."""

    code = "pokemon_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f"[{self.code}] {message}")


class InvalidPokemonIdentifier(PokemonError):
    code = "invalid_pokemon_identifier"


class PokemonNotFound(PokemonError):
    code = "pokemon_not_found"


class PokemonApiUnavailable(PokemonError):
    code = "pokemon_api_unavailable"


class PokemonApiResponseError(PokemonError):
    code = "pokemon_api_invalid_response"
