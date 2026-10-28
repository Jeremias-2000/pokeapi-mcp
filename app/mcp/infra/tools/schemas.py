"""Shared strict input schema types for tool signatures.

These annotations are enforced by the SDK at the protocol boundary, before
any tool code runs — the first deterministic input-guard layer. Use cases
re-validate after normalization (defense in depth).
"""

from typing import Annotated

from pydantic import Field

from app.mcp.application.usecases.identifiers import MAX_IDENTIFIER_LENGTH

Identifier = Annotated[str, Field(max_length=MAX_IDENTIFIER_LENGTH)]
PageSize = Annotated[int, Field(ge=1, le=100)]
PageOffset = Annotated[int, Field(ge=0)]
