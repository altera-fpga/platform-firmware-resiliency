"""ASCII table formatting for generated register documentation comments."""

from textwrap import wrap

from csr_gen.model import (
    Field,
    Register,
    register_address_end,
    register_has_address_range,
)


def field_bits_string(field: Field) -> str:
    """Format a field bit range for documentation tables."""
    if field.msb == field.lsb:
        return str(field.lsb)
    return f"{field.msb}:{field.lsb}"


def register_map_rows(registers: list[Register]) -> list[list[str]]:
    """Build register-map table rows sorted by address."""
    sorted_registers = sorted(registers, key=lambda register: register.address)
    return [
        [
            register.name,
            _format_register_address(register),
            register.description or "",
        ]
        for register in sorted_registers
    ]


def _format_register_address(register: Register) -> str:
    if register_has_address_range(register):
        return f"0x{register.address:02X}-0x{register_address_end(register):02X}"
    return f"0x{register.address:02X}"


def register_field_rows(register: Register) -> list[list[str]]:
    """Build per-register field table rows sorted by LSB."""
    sorted_fields = sorted(register.fields, key=lambda field: field.lsb)
    return [
        [
            field.name,
            field_bits_string(field),
            field.access,
            f"0x{field.reset:X}",
            field.description or "",
        ]
        for field in sorted_fields
    ]


def format_ascii_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    line_prefix: str = "",
    max_row_width: int = 80,
) -> list[str]:
    """Render an ASCII table with optional prefix on every output line."""
    max_table_width = max_row_width - len(line_prefix)
    widths = _column_widths(headers, rows, len(headers) - 1, max_table_width)
    lines: list[str] = []
    lines.append(_table_border(widths))
    lines.append(_table_row(headers, widths))
    lines.append(_table_border(widths))
    for row in rows:
        cell_lines = [_wrap_cell(cell, widths[index]) for index, cell in enumerate(row)]
        height = max(len(parts) for parts in cell_lines)
        for line_index in range(height):
            line_cells = [
                (
                    cell_lines[index][line_index]
                    if line_index < len(cell_lines[index])
                    else ""
                )
                for index in range(len(widths))
            ]
            lines.append(_table_row(line_cells, widths))
    lines.append(_table_border(widths))
    return [f"{line_prefix}{line}" for line in lines]


def _column_widths(
    headers: list[str],
    rows: list[list[str]],
    description_index: int,
    max_table_width: int,
) -> list[int]:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    while _table_row_width(widths) > max_table_width:
        if widths[description_index] > 1:
            widths[description_index] -= 1
        else:
            break
    return widths


def _table_row_width(widths: list[int]) -> int:
    return sum(width + 2 for width in widths) + len(widths) + 1


def _table_border(widths: list[int]) -> str:
    return "+" + "+".join("-" * (width + 2) for width in widths) + "+"


def _table_row(cells: list[str], widths: list[int]) -> str:
    parts = [f" {cell:<{width}} " for cell, width in zip(cells, widths, strict=True)]
    return "|" + "|".join(parts) + "|"


def _wrap_cell(text: str, width: int) -> list[str]:
    if width <= 0:
        return [""]
    if not text:
        return [""]
    if len(text) <= width:
        return [text]
    return wrap(
        text,
        width=width,
        break_long_words=True,
        break_on_hyphens=False,
    ) or [""]
