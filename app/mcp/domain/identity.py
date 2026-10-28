"""Request identity.

In a production Resource Server, `Identity` is derived exclusively from the
validated access token (`sub` claim) during stage 1 (authentication/scope) and
is immutable from that point on — tool arguments must never override it.

This study server performs no authentication, so the identity is a stand-in
(see infra/tools/identity.py) that exists to keep the "identity comes from the
transport, never from arguments" pattern visible in the code.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    sub: str
