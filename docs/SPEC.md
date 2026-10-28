# PokéAPI MCP – Tool Specification

Source: https://pokeapi.co/docs/v2 (read-only REST API, no auth). Data © PokéAPI; Pokémon is a trademark of Nintendo/Game Freak/Creatures.

## Conventions

- Identifier (`pokemon`, `move`, ...): name or numeric ID, normalized (Unicode NFKC, control/zero-width characters stripped, whitespace controls folded to spaces), trimmed, lower-cased, max 100 chars, matching `[a-z0-9-]+`. Otherwise → `invalid_pokemon_identifier`. The tool input schema also declares `maxLength: 100` on identifier parameters (protocol-boundary enforcement).
- Pagination: `limit` 1..100 (default 20), `offset` >= 0. Otherwise → `invalid_pokemon_identifier`.
  - List tools use PokéAPI-style offset pagination, returning `next_offset` / `previous_offset` (`null` at the ends). MCP cursor pagination (`nextCursor`) only applies to protocol list operations (`tools/list`, `resources/list`, `prompts/list`), not to `tools/call` results, so it is not used here. In mcp 2.2.0, `tools/list` returns all tools in one response.
- All tools are read-only (`readOnlyHint`, `idempotentHint`, `openWorldHint`) and return structured output.
- Errors (domain exceptions, stable `code`): `invalid_pokemon_identifier`, `pokemon_not_found` (HTTP 404), `pokemon_api_unavailable` (network/timeout), `pokemon_api_invalid_response` (non-404 HTTP error or malformed payload), `output_blocked` (output guardrail rejection).

## Guardrails

This server is a study skeleton for the MCP guardrail pipeline. Stage 1 (authentication/scope) is intentionally absent — see "Identity" below. Stage 6 (final response validation) belongs to the host/gateway and is out of scope for the server.

**Input guard (stage 2).** Tool arguments are validated twice: at the protocol boundary via strict schema annotations (`app/mcp/infra/tools/schemas.py`: `maxLength`, ranges) and again in use cases after normalization (`normalize_identifier`). Normalization always precedes validation so homoglyphs and zero-width characters cannot bypass the anchored pattern.

**Output guard (stage 4).** Use cases shape provider JSON into explicit allowlist DTOs — new upstream fields never leak without a code change. Additionally:

- Provider free text (`flavor_text`, `effect`, `genus`) is untrusted data: normalized, whitespace-collapsed, truncated to 500 chars, and wrapped in `<pokeapi_data>…</pokeapi_data>` delimiters that mark it as data, never instructions (indirect prompt-injection mitigation). Absent text is `null`.
- Provider-controlled URLs (`sprite`) pass an HTTPS + host allowlist (`raw.githubusercontent.com`); anything else becomes `null`.
- Nested collections are capped: ability `pokemon` at 50, encounters at 100.

**Output DLP + audit (stage 5).** Every tool result is serialized and scanned (`app/mcp/application/guardrails/dlp.py`) before leaving the server (`guard_output` decorator):

- BLOCK (whole response rejected with opaque `[output_blocked]`): Luhn-valid PANs, JWT/Bearer tokens, high-entropy strings, and any finding that only appears after normalization (evasion attempt).
- REDACT (masked as `[REDACTED:CPF]`): check-digit-valid CPF numbers.
- Fail closed: a scanner error blocks the response.
- Every decision (`input` deny, `output_dlp` allow/redact/block) is written to the `guardrails.audit` logger with `request_id`, `sub`, tool, reason, and finding counts by kind — never sensitive values.

**Identity (stage 3 pattern, simulated).** Tools receive an `Identity` derived from the transport — never from arguments. Since stage 1 is skipped, the identity is read from the optional `x-study-user` header (default `anonymous`) purely to exercise the data flow. Client headers are attacker-controlled; this is not authentication and must never feed authorization decisions.

## Tools

Free-text outputs (`genus`, `flavor_text`, `effect`) are delimited untrusted text, `null` when absent; `sprite` is `null` when not on the URL allowlist (see Guardrails).

| Tool | Input | PokéAPI endpoint | Output |
|---|---|---|---|
| `health_check` | – | – | `"ok"` |
| `get_pokemon_details` | `pokemon` | `GET /pokemon/{id}` | id, name, height, weight, base_experience, types[], abilities[{name,is_hidden}], stats{name:base}, sprite |
| `get_pokemon_species` | `pokemon` | `GET /pokemon-species/{id}` | id, name, color, habitat, generation, is_legendary, is_mythical, genus, flavor_text (first `en`), evolution_chain_id |
| `get_pokemon_evolution` | `pokemon` | species → `GET /evolution-chain/{id}` | pokemon, chain: nested `{species, evolves_to[]}` |
| `get_pokemon_encounters` | `pokemon` | `GET /pokemon/{id}/encounters` | [{location_area, versions[]}], capped at 100 |
| `get_type_matchups` | `type` | `GET /type/{id}` | id, name, damage_relations{relation:[type names]} |
| `get_move_details` | `move` | `GET /move/{id}` | id, name, type, damage_class, power, accuracy, pp, effect (en short) |
| `get_ability_details` | `ability` | `GET /ability/{id}` | id, name, effect (en short), pokemon[], capped at 50 |
| `get_item_details` | `item` | `GET /item/{id}` | id, name, category, cost, effect (en short), sprite |
| `list_pokemon` / `list_moves` / `list_abilities` / `list_items` | `limit`, `offset` | `GET /{resource}?limit&offset` | count, next_offset, previous_offset, results[{name}] |

## Layering

tool (`infra/tools`) → use case (`application/usecases`) → `PokemonApi` Protocol (`domain/interfaces/adapters`) → `PokeApiClient` (`infra/adapters`, httpx) → PokéAPI.
The adapter returns raw JSON; use cases validate input and shape output; tools log (with `request_id` and `sub`) and delegate.
Guardrail primitives live in `application/guardrails` (text normalization, URL allowlist, DLP detectors); the tool-boundary decorators (`guard_output`, `translate_errors`) and audit logger live in `infra/tools`.

## Acceptance

- Use cases are unit-tested with a fake `PokemonApi`.
- The adapter is tested with `httpx.MockTransport` (success, 404, 500, network error, bad JSON).
- Server boots; `tools/list` shows all tools; `tools/call` on a real endpoint succeeds.
