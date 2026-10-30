"""Hex literal parsing and formatting for CSR addresses and reset values."""

from __future__ import annotations

import re

_HEX_DIGITS = re.compile(r"^[0-9a-fA-F]+$")
_ADDRESS_RANGE = re.compile(
    r"^(?P<start>(?:0[xX])?[0-9a-fA-F]+)\s*-\s*(?P<end>(?:0[xX])?[0-9a-fA-F]+)$"
)
_FANCY_DASHES = frozenset("\u2013\u2014\u2212")  # en-dash, em-dash, minus sign


class HexLiteralError(ValueError):
    """Raised when an address or reset cell is not a valid hexadecimal literal."""


def _reject_fancy_dashes(text: str) -> None:
    if any(character in _FANCY_DASHES for character in text):
        raise HexLiteralError(
            "Address ranges must use an ASCII hyphen '-' "
            "(for example 0x8000-0x15ffff); en-dashes and other dash characters "
            "are not accepted."
        )


def parse_hex_literal(text: str) -> int:
    """Parse a hexadecimal literal; bare digit sequences are base 16."""
    stripped = text.strip()
    if not stripped:
        raise HexLiteralError("Value must not be empty.")
    if stripped.lower().startswith("0x"):
        digits = stripped[2:]
        if not digits or _HEX_DIGITS.fullmatch(digits) is None:
            raise HexLiteralError(
                "Value must be a hexadecimal literal (for example 0x10 or 10)."
            )
        return int(digits, 16)
    if _HEX_DIGITS.fullmatch(stripped) is None:
        raise HexLiteralError(
            "Value must be a hexadecimal literal (for example 0x10 or 10)."
        )
    return int(stripped, 16)


def format_hex_literal(value: int) -> str:
    """Format an integer as a normalized ``0x`` hexadecimal literal."""
    return f"0x{value:x}"


def normalize_address_text(text: str) -> str:
    """Normalize an address or inclusive range cell to ``0x`` hex form."""
    stripped = text.strip()
    if not stripped:
        raise HexLiteralError("Address must not be empty.")
    _reject_fancy_dashes(stripped)
    range_match = _ADDRESS_RANGE.fullmatch(stripped)
    if range_match is not None:
        start = parse_hex_literal(range_match.group("start"))
        end = parse_hex_literal(range_match.group("end"))
        return f"{format_hex_literal(start)}-{format_hex_literal(end)}"
    return format_hex_literal(parse_hex_literal(stripped))


def normalize_reset_text(text: str) -> str:
    """Normalize a reset cell to ``0x`` hex form."""
    return format_hex_literal(parse_hex_literal(text))


def parse_address_text(text: str) -> tuple[int, int | None]:
    """Parse an address cell into a byte offset and optional inclusive range end."""
    stripped = text.strip()
    _reject_fancy_dashes(stripped)
    range_match = _ADDRESS_RANGE.fullmatch(stripped)
    if range_match is not None:
        return (
            parse_hex_literal(range_match.group("start")),
            parse_hex_literal(range_match.group("end")),
        )
    return parse_hex_literal(stripped), None
