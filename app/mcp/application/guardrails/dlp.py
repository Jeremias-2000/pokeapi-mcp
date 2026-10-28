"""Data-loss-prevention detectors over serialized tool output.

This server only proxies public Pokémon data, so no sensitive values are
expected in output — which is exactly why a deterministic last barrier
matters: a DTO bug, a compromised upstream, or an injection-induced leak is
caught here before the response leaves the server.

Policy:
- BLOCK (reject the whole response): full PANs (Luhn-valid), tokens/secrets
  (JWT, Bearer), high-entropy strings, and any finding that only appears
  after normalization (evasion via separators, homoglyphs, or zero-width
  characters).
- REDACT (replace with a marker): validated CPF numbers.

Detectors use checksums (Luhn, CPF check digits), not regex alone, and the
text is normalized before detection to resist formatting-based evasion.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass
from enum import Enum

from app.mcp.application.guardrails.text import normalize_text


class Severity(Enum):
    REDACT = "redact"
    BLOCK = "block"


@dataclass(frozen=True)
class Finding:
    kind: str
    severity: Severity
    start: int
    end: int


@dataclass(frozen=True)
class ScanResult:
    findings: tuple[Finding, ...]
    evasion_detected: bool

    @property
    def blocked(self) -> bool:
        return self.evasion_detected or any(
            f.severity is Severity.BLOCK for f in self.findings
        )

    def count_by_kind(self) -> dict[str, int]:
        return dict(Counter(f.kind for f in self.findings))


_PAN = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_CPF = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
_JWT = re.compile(r"\b[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}\b")
_BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._~+-]{8,}")
_LONG_TOKEN = re.compile(r"[A-Za-z0-9_-]{32,}")
_HEX_TOKEN = re.compile(r"\b[0-9a-fA-F]{32,}\b")

_ENTROPY_THRESHOLD = 4.5
# Hex secrets cap at 4.0 bits/char; the floor rejects repeated-char false positives.
_HEX_ENTROPY_FLOOR = 3.0


def _luhn_ok(digits: str) -> bool:
    total = 0
    for position, char in enumerate(reversed(digits)):
        digit = int(char)
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _cpf_ok(digits: str) -> bool:
    if len(set(digits)) == 1:
        return False
    for size in (9, 10):
        weights = range(size + 1, 1, -1)
        total = sum(int(digit) * weight for digit, weight in zip(digits[:size], weights))
        if (total * 10 % 11) % 10 != int(digits[size]):
            return False
    return True


def _entropy(value: str) -> float:
    frequencies = Counter(value)
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in frequencies.values())


def _detect(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for match in _PAN.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            findings.append(Finding("pan", Severity.BLOCK, match.start(), match.end()))
    for match in _CPF.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        if _cpf_ok(digits):
            findings.append(Finding("cpf", Severity.REDACT, match.start(), match.end()))
    for match in _JWT.finditer(text):
        findings.append(Finding("token", Severity.BLOCK, match.start(), match.end()))
    for match in _BEARER.finditer(text):
        findings.append(Finding("token", Severity.BLOCK, match.start(), match.end()))
    for match in _LONG_TOKEN.finditer(text):
        if _entropy(match.group()) >= _ENTROPY_THRESHOLD:
            findings.append(Finding("secret", Severity.BLOCK, match.start(), match.end()))
    # Hex secrets cap at 4.0 bits/char, below the general entropy threshold.
    for match in _HEX_TOKEN.finditer(text):
        if _entropy(match.group()) < _HEX_ENTROPY_FLOOR:
            continue
        if not any(f.start <= match.start() and f.end >= match.end() for f in findings):
            findings.append(Finding("secret", Severity.BLOCK, match.start(), match.end()))
    return findings


def scan(text: str) -> ScanResult:
    """Scan text for sensitive data, including a normalized anti-evasion pass."""
    direct = _detect(text)
    evasive = _detect(normalize_text(text))
    evasion_detected = Counter(f.kind for f in evasive) > Counter(f.kind for f in direct)
    return ScanResult(findings=tuple(direct), evasion_detected=evasion_detected)


def redact(text: str, findings: tuple[Finding, ...]) -> str:
    """Replace REDACT findings with markers; spans must come from scan(text)."""
    result = text
    for finding in sorted(findings, key=lambda f: f.start, reverse=True):
        if finding.severity is Severity.REDACT:
            marker = f"[REDACTED:{finding.kind.upper()}]"
            result = result[: finding.start] + marker + result[finding.end :]
    return result
