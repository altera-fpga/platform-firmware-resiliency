"""Tests for GUI table cell commit normalization."""

from csr_gen_gui.table_editing import (
    COL_ADDRESS,
    COL_RESET,
    RowKind,
    commit_table_cell,
    table_row_to_dict,
)


def test_commit_table_cell_normalizes_address_on_register_row() -> None:
    row = table_row_to_dict(["CTRL", "10", "", "", "", "", "internal", "Control"])
    updated = commit_table_cell(row, COL_ADDRESS, kind=RowKind.REGISTER)
    assert updated["address"] == "0x10"


def test_commit_table_cell_normalizes_address_range() -> None:
    row = table_row_to_dict(["MEM", "20-2f", "", "", "", "", "external", "Memory"])
    updated = commit_table_cell(row, COL_ADDRESS, kind=RowKind.REGISTER)
    assert updated["address"] == "0x20-0x2f"


def test_commit_table_cell_normalizes_reset_on_field_row() -> None:
    row = table_row_to_dict(["", "", "ENABLE", "0", "rw", "0", "", "Enable"])
    updated = commit_table_cell(row, COL_RESET, kind=RowKind.FIELD)
    assert updated["reset"] == "0x0"


def test_commit_table_cell_leaves_invalid_address_unchanged() -> None:
    row = table_row_to_dict(["CTRL", "not-hex", "", "", "", "", "internal", ""])
    updated = commit_table_cell(row, COL_ADDRESS, kind=RowKind.REGISTER)
    assert updated["address"] == "not-hex"
