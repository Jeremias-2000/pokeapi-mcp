import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.mcp.application.guardrails.dlp import Severity, redact, scan

VALID_PAN = "4111 1111 1111 1111"  # Luhn-valid test number
VALID_CPF = "529.982.247-25"  # check-digit-valid test CPF
VALID_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxMjM0NTY3ODkwIn0"
    ".dozjgNryP4J3jVmNHl0w5N_LVgL1n3IywPlky0KqVhY"
)


def test_clean_text_has_no_findings() -> None:
    outcome = scan('{"name": "pikachu", "effect": "Inflicts damage."}')
    assert outcome.findings == ()
    assert not outcome.blocked


def test_luhn_valid_pan_with_spaces_blocks() -> None:
    outcome = scan(f"card {VALID_PAN} here")
    assert outcome.blocked
    assert outcome.findings[0].kind == "pan"
    assert outcome.findings[0].severity is Severity.BLOCK


def test_pan_failing_luhn_is_not_a_finding() -> None:
    outcome = scan("number 4111 1111 1111 1112")
    assert outcome.findings == ()


def test_valid_cpf_is_redacted_not_blocked() -> None:
    outcome = scan(f"cpf {VALID_CPF}")
    assert not outcome.blocked
    assert outcome.findings[0].kind == "cpf"
    assert redact(f"cpf {VALID_CPF}", outcome.findings) == "cpf [REDACTED:CPF]"


def test_cpf_with_invalid_check_digits_is_not_a_finding() -> None:
    outcome = scan("cpf 529.982.247-21")
    assert outcome.findings == ()


def test_jwt_blocks() -> None:
    outcome = scan(f"token: {VALID_JWT}")
    assert outcome.blocked
    assert outcome.findings[0].kind == "token"


def test_bearer_credential_blocks() -> None:
    outcome = scan("Authorization: Bearer abcdef1234567890")
    assert outcome.blocked


def test_high_entropy_string_blocks() -> None:
    outcome = scan("key aB3x9Kp2mN7qR4tV8wZ1yC6jF0hL5dGs")
    assert outcome.blocked
    assert outcome.findings[0].kind == "secret"


def test_low_entropy_long_string_does_not_block() -> None:
    outcome = scan("value " + "a" * 40)
    assert outcome.findings == ()


def test_hex_secret_blocks_despite_low_entropy_ceiling() -> None:
    outcome = scan("key 0123456789abcdef0123456789abcdef")
    assert outcome.blocked
    assert outcome.findings[0].kind == "secret"


def test_zero_width_evasion_is_detected_after_normalization() -> None:
    evasive = VALID_PAN.replace(" ", "\u200b")
    outcome = scan(evasive)
    assert outcome.blocked
    assert outcome.evasion_detected


def test_fullwidth_digits_evasion_is_detected() -> None:
    evasive = "".join(chr(0xFF10 + int(d)) for d in "4111111111111111")
    outcome = scan(evasive)
    assert outcome.blocked
