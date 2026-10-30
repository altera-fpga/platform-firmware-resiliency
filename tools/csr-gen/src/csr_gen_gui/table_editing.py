"""Headless CSR table row grouping and edit helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from csr_gen.literals import HexLiteralError, parse_address_text
from csr_gen.model import SUPPORTED_ACCESS, SUPPORTED_HW_ACCESS

from csr_gen_gui.model_table import TABLE_COLUMNS, dict_to_table_row, table_row_to_dict

ACCESS_CHOICES = tuple(sorted(SUPPORTED_ACCESS))
HW_ACCESS_CHOICES = tuple(sorted(SUPPORTED_HW_ACCESS))

COL_REGISTER = TABLE_COLUMNS.index("Register")
COL_ADDRESS = TABLE_COLUMNS.index("Address")
COL_FIELD = TABLE_COLUMNS.index("Field")
COL_BITS = TABLE_COLUMNS.index("Bits")
COL_ACCESS = TABLE_COLUMNS.index("Access")
COL_RESET = TABLE_COLUMNS.index("Reset")
COL_HW_ACCESS = TABLE_COLUMNS.index("HW Access")
COL_DESCRIPTION = TABLE_COLUMNS.index("Description")

_BIT_RANGE = re.compile(r"^(?P<msb>\d+)(?::(?P<lsb>\d+))?$")
_SORT_LAST = 2**62


class RowKind(str, Enum):
    REGISTER = "register"
    FIELD = "field"


@dataclass(frozen=True)
class TableRowInfo:
    """Metadata for one visible CSR table row."""

    kind: RowKind
    register_index: int
    field_index: int | None
    row_dict: dict[str, str]


def build_row_infos(rows: list[dict[str, str]]) -> list[TableRowInfo]:
    """Classify flat table rows into register and field entries."""
    infos: list[TableRowInfo] = []
    register_index = -1
    field_index = 0
    for row in rows:
        register_name = row.get("register", "").strip()
        address = row.get("address", "").strip()
        field_name = row.get("field", "").strip()
        if register_name and address and not field_name:
            register_index += 1
            field_index = 0
            infos.append(
                TableRowInfo(
                    kind=RowKind.REGISTER,
                    register_index=register_index,
                    field_index=None,
                    row_dict=row,
                )
            )
        elif field_name:
            infos.append(
                TableRowInfo(
                    kind=RowKind.FIELD,
                    register_index=register_index,
                    field_index=field_index,
                    row_dict=row,
                )
            )
            field_index += 1
    return infos


def expand_indicator(collapsed: bool) -> str:
    return "[+]" if collapsed else "[−]"


def register_cell_text(register_name: str, *, collapsed: bool) -> str:
    return f"{expand_indicator(collapsed)} {register_name}".strip()


def strip_register_indicator(text: str) -> str:
    value = text.strip()
    for prefix in ("[+]", "[−]", "[+] ", "[−] "):
        if value.startswith(prefix):
            return value[len(prefix) :].strip()
    return value


def visible_row_infos(
    infos: list[TableRowInfo],
    collapsed_registers: set[int],
) -> list[TableRowInfo]:
    """Return rows shown when some registers are collapsed."""
    visible: list[TableRowInfo] = []
    for info in infos:
        if info.kind == RowKind.FIELD and info.register_index in collapsed_registers:
            continue
        visible.append(info)
    return visible


def toggle_register_collapsed(collapsed: set[int], register_index: int) -> set[int]:
    """Return an updated collapsed-register set."""
    updated = set(collapsed)
    if register_index in updated:
        updated.remove(register_index)
    else:
        updated.add(register_index)
    return updated


def expand_register(collapsed: set[int], register_index: int) -> set[int]:
    """Return a collapsed-register set with one register expanded."""
    updated = set(collapsed)
    updated.discard(register_index)
    return updated


def visible_field_row_index(
    infos: list[TableRowInfo],
    collapsed_registers: set[int],
    register_index: int,
    field_index: int,
) -> int | None:
    """Return the visible table row index for one field, or None if hidden."""
    for visible_index, info in enumerate(
        visible_row_infos(infos, collapsed_registers),
    ):
        if (
            info.kind == RowKind.FIELD
            and info.register_index == register_index
            and info.field_index == field_index
        ):
            return visible_index
    return None


def visible_register_row_index(
    infos: list[TableRowInfo],
    collapsed_registers: set[int],
    register_index: int,
) -> int | None:
    """Return the visible table row index for one register definition row."""
    for visible_index, info in enumerate(
        visible_row_infos(infos, collapsed_registers),
    ):
        if info.kind == RowKind.REGISTER and info.register_index == register_index:
            return visible_index
    return None


def delete_register(
    rows: list[dict[str, str]], register_index: int
) -> list[dict[str, str]]:
    """Remove a register definition row and all of its field rows."""
    infos = build_row_infos(rows)
    if register_index < 0 or register_index >= _register_count(infos):
        return list(rows)
    delete_indices = {
        index
        for index, info in enumerate(infos)
        if info.register_index == register_index
    }
    return [row for index, row in enumerate(rows) if index not in delete_indices]


def delete_field_row(
    rows: list[dict[str, str]], row_index: int
) -> list[dict[str, str]]:
    """Remove one field row by flat row index."""
    infos = build_row_infos(rows)
    if row_index < 0 or row_index >= len(infos):
        return list(rows)
    if infos[row_index].kind != RowKind.FIELD:
        return list(rows)
    return [row for index, row in enumerate(rows) if index != row_index]


def insert_register_row(
    rows: list[dict[str, str]],
    at_index: int,
    *,
    name: str = "NEW_REG",
    address: str = "0x0",
    hw_access: str = "internal",
    description: str = "",
) -> list[dict[str, str]]:
    """Insert a register definition row before ``at_index`` in flat row space."""
    new_row = table_row_to_dict(
        [name, address, "", "", "", "", hw_access, description or name]
    )
    index = max(0, min(at_index, len(rows)))
    updated = list(rows)
    updated.insert(index, new_row)
    return updated


def insert_field_row(
    rows: list[dict[str, str]],
    at_index: int,
    *,
    name: str = "FIELD",
    bits: str = "0",
    access: str = "rw",
    reset: str = "0x0",
    description: str = "",
) -> list[dict[str, str]]:
    """Insert a field row before ``at_index`` in flat row space."""
    new_row = table_row_to_dict(
        ["", "", name, bits, access, reset, "", description or name]
    )
    index = max(0, min(at_index, len(rows)))
    updated = list(rows)
    updated.insert(index, new_row)
    return updated


def sort_table_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Sort register blocks by address and field rows by LSB within each register."""
    infos = build_row_infos(rows)
    blocks: list[tuple[dict[str, str], list[dict[str, str]], int]] = []

    register_row: dict[str, str] | None = None
    field_rows: list[dict[str, str]] = []
    block_order = 0

    for info in infos:
        if info.kind == RowKind.REGISTER:
            if register_row is not None:
                blocks.append((register_row, field_rows, block_order))
                block_order += 1
            register_row = dict(info.row_dict)
            field_rows = []
        elif info.kind == RowKind.FIELD and register_row is not None:
            field_rows.append(dict(info.row_dict))

    if register_row is not None:
        blocks.append((register_row, field_rows, block_order))

    blocks.sort(key=lambda item: _register_block_sort_key(item[0], item[2]))

    sorted_rows: list[dict[str, str]] = []
    for register, fields, _block_order in blocks:
        sorted_rows.append(register)
        ordered_fields = sorted(
            enumerate(fields),
            key=lambda item: _field_row_sort_key(item[1], item[0]),
        )
        sorted_rows.extend(field_row for _, field_row in ordered_fields)
    return sorted_rows


def table_rows_need_sort(rows: list[dict[str, str]]) -> bool:
    """Return whether ``sort_table_rows`` would change the table."""
    if len(rows) < 2:
        return False
    return sort_table_rows(rows) != rows


def read_row_values(values: list[str]) -> dict[str, str]:
    """Normalize GUI row values and strip register expand indicators."""
    row = table_row_to_dict(values)
    if row["register"]:
        row["register"] = strip_register_indicator(row["register"])
    return row


def commit_table_cell(
    row: dict[str, str],
    column: int,
    *,
    kind: RowKind,
) -> dict[str, str]:
    """Apply shared address and reset normalization after a table cell edit."""
    from csr_gen.literals import (
        HexLiteralError,
        normalize_address_text,
        normalize_reset_text,
    )

    updated = dict(row)
    if (
        kind == RowKind.REGISTER
        and column == COL_ADDRESS
        and updated["address"].strip()
    ):
        try:
            updated["address"] = normalize_address_text(updated["address"])
        except HexLiteralError:
            pass
    elif kind == RowKind.FIELD and column == COL_RESET and updated["reset"].strip():
        try:
            updated["reset"] = normalize_reset_text(updated["reset"])
        except HexLiteralError:
            pass
    return updated


def _register_count(infos: list[TableRowInfo]) -> int:
    if not infos:
        return 0
    return max(info.register_index for info in infos) + 1


def _register_block_sort_key(
    register_row: dict[str, str], order: int
) -> tuple[int, int]:
    address_text = register_row.get("address", "").strip()
    if not address_text:
        return (_SORT_LAST, order)
    try:
        start, _end = parse_address_text(address_text)
        return (start, order)
    except HexLiteralError:
        return (_SORT_LAST - 1, order)


def _field_row_sort_key(field_row: dict[str, str], order: int) -> tuple[int, int, int]:
    bits_value = field_row.get("bits", "").strip()
    match = _BIT_RANGE.fullmatch(bits_value)
    if match is None:
        return (_SORT_LAST, _SORT_LAST, order)
    msb = int(match.group("msb"))
    lsb = int(match.group("lsb") or msb)
    return (lsb, msb, order)


@dataclass(frozen=True)
class FieldInsertActions:
    """Which Add field context-menu actions apply to the clicked row."""

    above: bool
    below: bool


def register_field_count(infos: list[TableRowInfo], register_index: int) -> int:
    """Return how many field rows belong to a register."""
    return sum(
        1
        for info in infos
        if info.kind == RowKind.FIELD and info.register_index == register_index
    )


def field_insert_actions(
    info: TableRowInfo,
    row_infos: list[TableRowInfo],
) -> FieldInsertActions:
    """Whether Add field above/below apply to the clicked row."""
    if info.kind == RowKind.FIELD:
        return FieldInsertActions(above=True, below=True)
    if info.kind == RowKind.REGISTER:
        if register_field_count(row_infos, info.register_index) == 0:
            return FieldInsertActions(above=False, below=True)
        return FieldInsertActions(above=False, below=False)
    return FieldInsertActions(above=False, below=False)


def field_insert_row_index(
    rows: list[dict[str, str]],
    *,
    register_index: int,
    field_index: int | None,
) -> int | None:
    """Return the flat row index to insert a new field for the current selection."""
    infos = build_row_infos(rows)
    register_row_index: int | None = None
    last_field_row_index: int | None = None
    selected_field_row_index: int | None = None
    for flat_index, info in enumerate(infos):
        if info.register_index != register_index:
            continue
        if info.kind == RowKind.REGISTER:
            register_row_index = flat_index
        elif info.kind == RowKind.FIELD:
            last_field_row_index = flat_index
            if field_index is not None and info.field_index == field_index:
                selected_field_row_index = flat_index
    if register_row_index is None:
        return None
    if selected_field_row_index is not None:
        return selected_field_row_index + 1
    if last_field_row_index is None:
        return register_row_index + 1
    return last_field_row_index + 1
