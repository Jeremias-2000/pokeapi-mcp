"""Simulated identity extraction — a study placeholder, NOT authentication.

A real Resource Server validates a Bearer token (JWKS, iss/aud/exp, scopes)
and builds `Identity` from its `sub` claim. This server skips stage 1 by
decision, so the identity is read from an optional `x-study-user` header to
keep the data flow (transport → Identity → logs/audit) exercised.

WARNING: client-supplied headers are attacker-controlled. Never treat this
value as an identity assertion for authorization decisions.
"""

from mcp.server.mcpserver.context import Context

from app.mcp.domain.identity import Identity

ANONYMOUS = Identity(sub="anonymous")
_STUDY_HEADER = "x-study-user"


def identity_from_context(ctx: Context | None) -> Identity:
    if ctx is None:
        return ANONYMOUS
    try:
        headers = ctx.headers
    except ValueError:
        return ANONYMOUS
    if not headers:
        return ANONYMOUS
    candidate = headers.get(_STUDY_HEADER, "").strip()
    if not candidate or len(candidate) > 100:
        return ANONYMOUS
    return Identity(sub=candidate)
