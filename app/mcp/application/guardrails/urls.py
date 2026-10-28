"""Allowlist validation for provider-controlled URLs.

Provider JSON can carry arbitrary URLs (sprites, linked resources). Only URLs
on an explicit host allowlist may reach the LLM context; anything else is
dropped. This blunts rendering-based exfiltration if the upstream data source
is ever compromised or hostile.
"""

from urllib.parse import urlparse

ALLOWED_MEDIA_HOSTS = frozenset({"raw.githubusercontent.com"})


def allowlisted_url(
    value: object, allowed_hosts: frozenset[str] = ALLOWED_MEDIA_HOSTS
) -> str | None:
    """Return the URL only if it is HTTPS on an allowlisted host, else None."""
    if not isinstance(value, str) or not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        return None
    return value
