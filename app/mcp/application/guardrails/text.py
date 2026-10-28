"""Text normalization and untrusted-data sanitization.

Normalization always runs *before* validation or detection: Unicode NFKC plus
removal of control (Cc) and format (Cf, e.g. zero-width) characters, so that
homoglyphs and invisible characters cannot bypass anchored patterns.
"""

import re
import unicodedata

UNTRUSTED_DATA_TAG = "pokeapi_data"
MAX_UNTRUSTED_TEXT_LENGTH = 500

_DELIMITER = re.compile(r"</?\s*pokeapi_data\s*>", re.IGNORECASE)

_DROPPED_CATEGORIES = frozenset({"Cc", "Cf"})
_WHITESPACE_CONTROLS = frozenset("\n\r\t\f\v")


def normalize_text(value: str) -> str:
    """Apply Unicode NFKC, fold whitespace controls to spaces, strip the rest.

    Whitespace-like control characters (newline, tab, ...) become spaces so
    words do not fuse; other control (Cc) and format (Cf, e.g. zero-width)
    characters are removed.
    """
    normalized = unicodedata.normalize("NFKC", value)
    chars: list[str] = []
    for ch in normalized:
        if ch in _WHITESPACE_CONTROLS:
            chars.append(" ")
        elif unicodedata.category(ch) not in _DROPPED_CATEGORIES:
            chars.append(ch)
    return "".join(chars)


def sanitize_untrusted_text(
    value: str | None, max_length: int = MAX_UNTRUSTED_TEXT_LENGTH
) -> str | None:
    """Sanitize provider free text before it enters the LLM context.

    The text is normalized, whitespace-collapsed, truncated, and wrapped in
    delimiters that mark it as data — never instructions — to the host model
    (indirect prompt-injection mitigation).
    """
    if value is None:
        return None
    cleaned = " ".join(normalize_text(value).split())
    # Neutralize embedded delimiters (any case/spacing) so provider text
    # cannot close the tag early and escape the "data, never instructions"
    # framing.
    cleaned = " ".join(_DELIMITER.sub(" ", cleaned).split())
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip() + "…"
    return f"<{UNTRUSTED_DATA_TAG}>{cleaned}</{UNTRUSTED_DATA_TAG}>"
