"""Unit tests for ASCII table formatting helpers."""

from csr_gen.output.ascii_tables import (
    _column_widths,
    _wrap_cell,
    format_ascii_table,
)


def test_format_ascii_table_stops_shrinking_at_minimum_description_width() -> None:
    """When the table cannot fit, width reduction stops at description width 1."""
    headers = ["Register", "Address", "Description"]
    rows = [
        ["VERY_LONG_REGISTER", "0x00000000", "x"],
    ]
    widths = _column_widths(headers, rows, description_index=2, max_table_width=12)
    assert widths[2] == 1


def test_wrap_cell_returns_empty_string_for_non_positive_width() -> None:
    assert _wrap_cell("overflow", 0) == [""]
    assert _wrap_cell("text", -1) == [""]


def test_format_ascii_table_wraps_multiline_description() -> None:
    lines = format_ascii_table(
        ["Field", "Description"],
        [["EN", "A long description that should wrap across lines"]],
        max_row_width=40,
        line_prefix="// ",
    )
    assert any("long description" in line for line in lines)
    assert all(line.startswith("// ") for line in lines)
