import re

from app.mcp.application.guardrails.text import normalize_text
from app.mcp.domain.exceptions import InvalidPokemonIdentifier

MAX_IDENTIFIER_LENGTH = 100

_IDENTIFIER = re.compile(r"[a-z0-9-]+")


def normalize_identifier(value: str, label: str = "identifier") -> str:
    # Normalize (NFKC, strip control/zero-width chars) *before* validating so
    # homoglyphs and invisible characters cannot bypass the anchored pattern.
    identifier = normalize_text(value).strip().lower()
    if (
        not identifier
        or len(identifier) > MAX_IDENTIFIER_LENGTH
        or not _IDENTIFIER.fullmatch(identifier)
    ):
        raise InvalidPokemonIdentifier(
            f"{label} must be a name or ID containing only letters, numbers, or hyphens"
        )
    return identifier
