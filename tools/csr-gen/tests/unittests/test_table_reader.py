"""Unit tests for shared Markdown/CSV table parsing."""

import pytest

from csr_gen.errors import CsrValidationError
from csr_gen.input.table_reader import (
    TableParseError,
    _parse_address,
    parse_csr_table,
    rows_to_register_drafts,
)

HEADER = [
    "Register",
    "Address",
    "Field",
    "Bits",
    "Access",
    "Reset",
    "Description",
    "HW Access",
]


def test_parse_csr_table_rejects_empty_header() -> None:
    with pytest.raises(TableParseError, match="header row"):
        parse_csr_table(
            [], [["CTRL", "0x00", "EN", "0", "rw", "0", "", ""]], location="t"
        )


def test_parse_csr_table_rejects_header_without_body() -> None:
    with pytest.raises(TableParseError, match="at least one data row"):
        parse_csr_table(HEADER, [], location="t")


def test_parse_csr_table_pads_short_rows() -> None:
    rows, has_reset = parse_csr_table(
        HEADER,
        [["CTRL", "0x00", "EN", "0"]],
        location="t",
    )
    assert has_reset
    assert rows[0]["description"] == ""
    assert rows[0]["hw access"] == ""


def test_register_definition_row_rejects_invalid_address() -> None:
    rows, has_reset = parse_csr_table(
        HEADER,
        [
            ["CTRL", "not-an-address", "", "", "", "", "Control", ""],
            ["", "", "EN", "0", "rw", "0", "Enable", ""],
        ],
        location="t",
    )
    errors, drafts = rows_to_register_drafts(rows, has_reset_column=has_reset)
    assert not drafts
    assert any("Address must be a hexadecimal literal" in error for error in errors)


def test_register_definition_row_rejects_invalid_hw_access() -> None:
    rows, has_reset = parse_csr_table(
        HEADER,
        [
            ["CTRL", "0x00", "", "", "", "", "Control", "bogus"],
            ["", "", "EN", "0", "rw", "0", "Enable", ""],
        ],
        location="t",
    )
    errors, drafts = rows_to_register_drafts(rows, has_reset_column=has_reset)
    assert not drafts
    assert any("HW Access must be one of" in error for error in errors)


def test_register_definition_row_rejects_nonempty_access() -> None:
    rows, has_reset = parse_csr_table(
        HEADER,
        [
            ["CTRL", "0x00", "", "", "rw", "", "Control", ""],
            ["", "", "EN", "0", "rw", "0", "Enable", ""],
        ],
        location="t",
    )
    errors, _drafts = rows_to_register_drafts(rows, has_reset_column=has_reset)
    assert any(
        "Access must be empty on a register definition row" in error for error in errors
    )


def test_register_definition_row_rejects_nonempty_reset() -> None:
    rows, has_reset = parse_csr_table(
        HEADER,
        [
            ["CTRL", "0x00", "", "", "", "0", "Control", ""],
            ["", "", "EN", "0", "rw", "0", "Enable", ""],
        ],
        location="t",
    )
    errors, _drafts = rows_to_register_drafts(rows, has_reset_column=has_reset)
    assert any(
        "Reset must be empty on a register definition row" in error for error in errors
    )


def test_parse_address_rejects_invalid_range_endpoints() -> None:
    errors, _start, _end = _parse_address("0-0g8", 1, None)
    assert errors
    assert "Address must be a hexadecimal literal" in errors[0]


def test_rows_to_register_model_raises_on_errors() -> None:
    from csr_gen.input.table_reader import rows_to_register_model

    rows, has_reset = parse_csr_table(
        HEADER,
        [["CTRL", "0x00", "", "", "", "", "Control", ""]],
        location="t",
    )
    with pytest.raises(CsrValidationError, match="at least one field"):
        rows_to_register_model(rows, has_reset_column=has_reset, subsection="Sub A")
