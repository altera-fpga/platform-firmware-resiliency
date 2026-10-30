"""Convert between RegisterModel and flat CSR table rows for the GUI editor."""

from __future__ import annotations

from csr_gen.literals import format_hex_literal
from csr_gen.model import (
    Field,
    Register,
    RegisterModel,
    collect_register_draft_errors,
    register_address_end,
    register_has_address_range,
)
from csr_gen.input.table_reader import rows_to_register_drafts

TABLE_COLUMNS = (
    "Register",
    "Address",
    "Field",
    "Bits",
    "Access",
    "Reset",
    "HW Access",
    "Description",
)

_ROW_KEYS = (
    "register",
    "address",
    "field",
    "bits",
    "access",
    "reset",
    "hw access",
    "description",
)

_DEFAULT_ACCESS = "rw"


def model_to_row_dicts(model: RegisterModel) -> list[dict[str, str]]:
    """Render a register model as normalized lowercase-key row dicts."""
    rows: list[dict[str, str]] = []
    for register in model.registers:
        rows.append(_register_definition_row(register))
        for register_field in register.fields:
            rows.append(_field_row(register_field))
    return rows


def row_dicts_to_model(
    rows: list[dict[str, str]],
    *,
    allow_incomplete: bool = False,
) -> tuple[RegisterModel | None, list[str]]:
    """Parse table rows into a model, returning all validation errors."""
    if not rows:
        return RegisterModel(), []
    errors, drafts = rows_to_register_drafts(
        rows,
        has_reset_column=True,
        first_row_number=1,
    )
    errors.extend(
        collect_register_draft_errors(
            drafts,
            allow_empty_fields=allow_incomplete,
        )
    )
    if errors and not allow_incomplete:
        return None, errors
    if not drafts:
        return None, errors
    from csr_gen.model import drafts_to_model

    return drafts_to_model(drafts), errors


def table_row_to_dict(values: list[str]) -> dict[str, str]:
    """Map GUI column values to normalized row dict keys."""
    padded = values + [""] * len(_ROW_KEYS)
    return {key: padded[index].strip() for index, key in enumerate(_ROW_KEYS)}


def dict_to_table_row(row: dict[str, str]) -> list[str]:
    """Map a normalized row dict to GUI column values."""
    return [row.get(key, "") for key in _ROW_KEYS]


def _register_definition_row(register: Register) -> dict[str, str]:
    return {
        "register": register.name,
        "address": _format_address(register),
        "field": "",
        "bits": "",
        "access": "",
        "reset": "",
        "hw access": register.hw_access,
        "description": register.description or register.name,
    }


def _field_row(register_field: Field) -> dict[str, str]:
    return {
        "register": "",
        "address": "",
        "field": register_field.name,
        "bits": _format_bits(register_field),
        "access": register_field.access or _DEFAULT_ACCESS,
        "reset": _format_reset(register_field.reset),
        "hw access": "",
        "description": register_field.description or register_field.name,
    }


def _format_address(register: Register) -> str:
    if register_has_address_range(register):
        return (
            f"{format_hex_literal(register.address)}-"
            f"{format_hex_literal(register_address_end(register))}"
        )
    return format_hex_literal(register.address)


def _format_bits(register_field: Field) -> str:
    if register_field.msb == register_field.lsb:
        return str(register_field.msb)
    return f"{register_field.msb}:{register_field.lsb}"


def _format_reset(reset: int) -> str:
    return format_hex_literal(reset)


def make_ranged_external_register(
    *,
    name: str,
    address_start: int,
    address_end: int,
    field_name: str,
    access: str,
    reset: int,
    description: str,
) -> Register:
    """Build a ranged external register with one 31:0 field."""
    return Register(
        name=name.strip().upper(),
        address=address_start,
        address_end=address_end,
        description=description.strip() or name.strip(),
        hw_access="external",
        fields=[
            Field(
                name=field_name.strip().upper() or name.strip().upper(),
                msb=31,
                lsb=0,
                access=access.strip().lower() or _DEFAULT_ACCESS,
                reset=reset,
                description=description.strip() or field_name.strip() or name.strip(),
            ),
        ],
    )
