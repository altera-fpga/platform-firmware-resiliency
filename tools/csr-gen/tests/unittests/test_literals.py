"""Tests for hexadecimal literal parsing and formatting."""

import pytest

from csr_gen.literals import (
    HexLiteralError,
    format_hex_literal,
    normalize_address_text,
    normalize_reset_text,
    parse_address_text,
    parse_hex_literal,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0x10", 16),
        ("0X10", 16),
        ("10", 16),
        ("0", 0),
        ("ff", 255),
    ],
)
def test_parse_hex_literal(text: str, expected: int) -> None:
    assert parse_hex_literal(text) == expected


def test_parse_hex_literal_rejects_decimal_only_phrasing() -> None:
    with pytest.raises(HexLiteralError):
        parse_hex_literal("not-hex")


def test_normalize_address_text_single_offset() -> None:
    assert normalize_address_text("10") == "0x10"


def test_normalize_address_text_range() -> None:
    assert normalize_address_text("20-2f") == "0x20-0x2f"


def test_parse_address_text_range() -> None:
    start, end = parse_address_text("0x0-0xc")
    assert start == 0
    assert end == 0xC


def test_format_hex_literal() -> None:
    assert format_hex_literal(0) == "0x0"
    assert format_hex_literal(16) == "0x10"


def test_normalize_reset_text() -> None:
    assert normalize_reset_text("0") == "0x0"
    assert normalize_reset_text("0x1") == "0x1"


def test_parse_address_rejects_en_dash_range() -> None:
    with pytest.raises(HexLiteralError, match="ASCII hyphen"):
        parse_address_text("0x0\u20130xc")


def test_normalize_address_text_rejects_en_dash() -> None:
    with pytest.raises(HexLiteralError, match="ASCII hyphen"):
        normalize_address_text("0x10\u20140x20")
