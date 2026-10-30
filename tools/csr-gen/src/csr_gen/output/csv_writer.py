"""Serialize CSR register models to CSV register tables."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from csr_gen.model import DEFAULT_HW_ACCESS, Field, Register, RegisterModel
from csr_gen.output.markdown_writer import DEFAULT_ACCESS, MARKDOWN_COLUMNS
from csr_gen.output.register_order import sorted_fields, sorted_registers

CSV_COLUMNS = MARKDOWN_COLUMNS


def write_csv_file(path: Path, model: RegisterModel) -> None:
    """Write a CSV CSR specification to a file."""
    path.write_text(write_csv(model), encoding="utf-8", newline="")


def write_csv(model: RegisterModel) -> str:
    """Render a register model as a CSV table with canonical columns."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for register in sorted_registers(model):
        writer.writerows(_register_rows(register))
    return buffer.getvalue()


def _register_rows(register: Register) -> list[list[str]]:
    rows: list[list[str]] = []
    hw_access = register.hw_access or DEFAULT_HW_ACCESS
    rows.append(
        _table_row(
            register=register.name,
            address=_format_address(register),
            field="",
            bits="",
            access="",
            reset="",
            description=register.description or register.name,
            hw_access=hw_access,
        )
    )
    for register_field in sorted_fields(register):
        rows.append(
            _table_row(
                register="",
                address="",
                field=register_field.name,
                bits=_format_bits(register_field),
                access=register_field.access or DEFAULT_ACCESS,
                reset=_format_reset(register_field.reset),
                description=register_field.description or register_field.name,
                hw_access="",
            )
        )
    return rows


def _table_row(
    *,
    register: str,
    address: str,
    field: str,
    bits: str,
    access: str,
    reset: str,
    description: str,
    hw_access: str,
) -> list[str]:
    return [
        register,
        address,
        field,
        bits,
        access,
        reset,
        hw_access,
        description,
    ]


def _format_address(register: Register) -> str:
    if register.address_end is not None:
        return f"{register.address:#x}-{register.address_end:#x}"
    return f"{register.address:#x}"


def _format_bits(register_field: Field) -> str:
    if register_field.msb == register_field.lsb:
        return str(register_field.msb)
    return f"{register_field.msb}:{register_field.lsb}"


def _format_reset(reset: int) -> str:
    return f"{reset:#x}"
