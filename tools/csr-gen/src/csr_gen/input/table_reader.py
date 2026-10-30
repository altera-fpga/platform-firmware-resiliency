"""Parse CSR register tables from row-oriented tabular data (Markdown or CSV)."""

from __future__ import annotations

import re

from csr_gen.errors import CsrGenError, CsrValidationError
from csr_gen.literals import HexLiteralError, parse_address_text, parse_hex_literal
from csr_gen.model import (
    DEFAULT_HW_ACCESS,
    FieldDraft,
    RegisterDraft,
    RegisterModel,
    SUPPORTED_HW_ACCESS,
    collect_register_draft_errors,
    drafts_to_model,
    row_error,
)

REQUIRED_COLUMNS = frozenset(
    {
        "register",
        "address",
        "field",
        "bits",
    }
)
OPTIONAL_COLUMNS = frozenset({"access", "description", "hw access", "reset"})
EXPECTED_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS
DEFAULT_ACCESS = "rw"
_BIT_RANGE = re.compile(r"^(?P<msb>\d+)(?::(?P<lsb>\d+))?$")


class TableParseError(CsrGenError):
    """Raised when a CSR table header or structure cannot be parsed."""


def parse_csr_table(
    header_cells: list[str],
    body_rows: list[list[str]],
    *,
    location: str,
    subsection: str | None = None,
) -> tuple[list[dict[str, str]], bool]:
    """
    Validate header columns and normalize body rows.

    Returns normalized row dicts and whether a Reset column is present.
    """
    if not header_cells:
        raise TableParseError(f"{location} must contain a header row.")
    if not body_rows:
        raise TableParseError(
            f"{location} must contain a header and at least one data row."
        )

    columns = [cell.strip().casefold() for cell in header_cells]
    column_set = set(columns)
    if len(columns) != len(column_set):
        raise TableParseError(f"{location} must not contain duplicate column names.")
    if not REQUIRED_COLUMNS.issubset(column_set):
        missing = ", ".join(sorted(REQUIRED_COLUMNS - column_set))
        hint = ""
        if subsection is not None:
            hint = (
                " Tables under a CSR bank section (including ### subsections) "
                "must use CSR columns (Register, Address, Field, Bits, …). "
                "Move documentation tables outside the bank section."
            )
        raise TableParseError(
            f"{location} is missing required column(s): {missing}.{hint}"
        )
    unknown = column_set - EXPECTED_COLUMNS
    if unknown:
        raise TableParseError(
            f"{location} has unsupported column(s): "
            + ", ".join(sorted(unknown))
            + ". "
            f"Supported columns are required {', '.join(sorted(REQUIRED_COLUMNS))} "
            f"and optional {', '.join(sorted(OPTIONAL_COLUMNS))}."
        )
    has_reset_column = "reset" in column_set
    normalized = [_normalize_row(columns, row) for row in body_rows]
    return normalized, has_reset_column


def rows_to_register_drafts(
    rows: list[dict[str, str]],
    *,
    has_reset_column: bool,
    subsection: str | None = None,
    first_row_number: int = 1,
) -> tuple[list[str], list[RegisterDraft]]:
    """Parse normalized rows into register drafts and collect per-table row errors."""
    return _collect_row_and_model_errors(
        rows,
        subsection,
        has_reset_column=has_reset_column,
        first_row_number=first_row_number,
    )


def rows_to_register_model(
    rows: list[dict[str, str]],
    *,
    has_reset_column: bool,
    subsection: str | None = None,
    first_row_number: int = 1,
) -> RegisterModel:
    """Build a register model from normalized table rows."""
    errors, drafts = rows_to_register_drafts(
        rows,
        has_reset_column=has_reset_column,
        subsection=subsection,
        first_row_number=first_row_number,
    )
    errors.extend(collect_register_draft_errors(drafts))
    if errors:
        raise CsrValidationError(errors)
    return drafts_to_model(drafts)


def _table_row_error(subsection: str | None, row_number: int, message: str) -> str:
    if subsection is None:
        return row_error(row_number, message)
    return f"CSR table in subsection {subsection!r} row {row_number}: {message}"


def _collect_row_and_model_errors(
    rows: list[dict[str, str]],
    subsection: str | None,
    *,
    has_reset_column: bool,
    first_row_number: int = 1,
) -> tuple[list[str], list[RegisterDraft]]:
    errors: list[str] = []
    drafts: list[RegisterDraft] = []
    current_register: RegisterDraft | None = None

    for row_number, row in enumerate(rows, start=first_row_number):
        register_name = row["register"].strip()
        address = row["address"].strip()
        field_name = row["field"].strip()
        row_errors = _collect_row_structure_errors(
            subsection,
            row_number,
            register_name,
            address,
            field_name,
            current_register,
        )
        if row_errors:
            errors.extend(row_errors)
            continue

        has_register = bool(register_name and address)
        has_field = bool(field_name)

        if has_register and not has_field:
            definition_errors = _validate_register_definition_row(
                row, row_number, subsection, has_reset_column=has_reset_column
            )
            if definition_errors:
                errors.extend(definition_errors)
                continue
            address_errors, parsed_address, address_end = _parse_address(
                address, row_number, subsection
            )
            if address_errors:
                errors.extend(address_errors)
                continue
            hw_access_errors, hw_access = _parse_hw_access(
                row.get("hw access", ""), row_number, subsection
            )
            if hw_access_errors:
                errors.extend(hw_access_errors)
                continue
            current_register = RegisterDraft(
                row_number=row_number,
                name=register_name,
                address=parsed_address,
                description=_register_description(row, register_name),
                hw_access=hw_access,
                address_end=address_end,
                fields=[],
            )
            drafts.append(current_register)
            continue

        field_errors, field_draft = _parse_field_draft(
            row, row_number, subsection, has_reset_column=has_reset_column
        )
        if field_errors:
            errors.extend(field_errors)
            continue

        if has_register and has_field:
            address_errors, parsed_address, address_end = _parse_address(
                address, row_number, subsection
            )
            if address_errors:
                errors.extend(address_errors)
                continue
            hw_access_errors, hw_access = _parse_hw_access(
                row.get("hw access", ""), row_number, subsection
            )
            if hw_access_errors:
                errors.extend(hw_access_errors)
                continue
            shared_description = _shared_description(row, field_name)
            field_draft.description = shared_description
            current_register = RegisterDraft(
                row_number=row_number,
                name=register_name,
                address=parsed_address,
                description=shared_description,
                hw_access=hw_access,
                address_end=address_end,
                fields=[field_draft],
            )
            drafts.append(current_register)
        elif current_register is not None:
            if row.get("hw access", "").strip():
                errors.append(
                    _table_row_error(
                        subsection,
                        row_number,
                        "HW Access must only be set on the register definition row.",
                    )
                )
                continue
            current_register.fields.append(field_draft)

    return errors, drafts


def _collect_row_structure_errors(
    subsection: str | None,
    row_number: int,
    register_name: str,
    address: str,
    field_name: str,
    current_register: RegisterDraft | None,
) -> list[str]:
    errors: list[str] = []
    has_register = bool(register_name)
    has_address = bool(address)
    has_field = bool(field_name)
    if has_register != has_address:
        errors.append(
            _table_row_error(
                subsection, row_number, "Must provide both Register and Address."
            )
        )
    if not has_register and not has_field:
        errors.append(
            _table_row_error(
                subsection,
                row_number,
                "Must declare a register definition row or a Field.",
            )
        )
    if not has_register and has_field and current_register is None:
        errors.append(
            _table_row_error(
                subsection, row_number, "Continues a register before one is declared."
            )
        )
    return errors


def _validate_register_definition_row(
    row: dict[str, str],
    row_number: int,
    subsection: str | None,
    *,
    has_reset_column: bool,
) -> list[str]:
    errors: list[str] = []
    if row["bits"].strip():
        errors.append(
            _table_row_error(
                subsection,
                row_number,
                "Bits must be empty on a register definition row.",
            )
        )
    if row["access"].strip():
        errors.append(
            _table_row_error(
                subsection,
                row_number,
                "Access must be empty on a register definition row.",
            )
        )
    if has_reset_column and row["reset"].strip():
        errors.append(
            _table_row_error(
                subsection,
                row_number,
                "Reset must be empty on a register definition row.",
            )
        )
    return errors


def _parse_hw_access(
    value: str, row_number: int, subsection: str | None
) -> tuple[list[str], str]:
    normalized = value.strip().casefold()
    if not normalized:
        return [], DEFAULT_HW_ACCESS
    if normalized not in SUPPORTED_HW_ACCESS:
        return [
            _table_row_error(
                subsection,
                row_number,
                f"HW Access must be one of: {', '.join(sorted(SUPPORTED_HW_ACCESS))}.",
            )
        ], DEFAULT_HW_ACCESS
    return [], normalized


def _parse_address(
    value: str, row_number: int, subsection: str | None
) -> tuple[list[str], int, int | None]:
    stripped = value.strip()
    if not stripped:
        return (
            [
                _table_row_error(
                    subsection,
                    row_number,
                    "Address must not be empty.",
                )
            ],
            0,
            None,
        )
    try:
        parsed_address, address_end = parse_address_text(stripped)
    except HexLiteralError:
        return (
            [
                _table_row_error(
                    subsection,
                    row_number,
                    "Address must be a hexadecimal literal or inclusive "
                    "byte-offset range (for example 0x00-0x0C).",
                )
            ],
            0,
            None,
        )
    return [], parsed_address, address_end


def _parse_field_draft(
    row: dict[str, str],
    row_number: int,
    subsection: str | None,
    *,
    has_reset_column: bool,
) -> tuple[list[str], FieldDraft]:
    errors: list[str] = []
    bits_value = row["bits"].strip()
    access_value = row["access"].strip() or DEFAULT_ACCESS
    reset_value = row["reset"].strip()
    field_name = row["field"].strip()
    description_value = _field_description(row, field_name)

    if not bits_value:
        errors.append(
            _table_row_error(subsection, row_number, "Bits must not be empty.")
        )

    msb = 0
    lsb = 0
    if bits_value:
        bits = _BIT_RANGE.fullmatch(bits_value)
        if bits is None:
            errors.append(
                _table_row_error(
                    subsection,
                    row_number,
                    "Bits must be a bit index or msb:lsb range.",
                )
            )
        else:
            msb = int(bits.group("msb"))
            lsb = int(bits.group("lsb") or bits.group("msb"))

    reset = 0
    if has_reset_column:
        if not reset_value:
            errors.append(
                _table_row_error(subsection, row_number, "Reset must not be empty.")
            )
        else:
            reset_errors, reset = _parse_reset(reset_value, row_number, subsection)
            errors.extend(reset_errors)

    if errors:
        return errors, FieldDraft(
            row_number=row_number,
            name=field_name,
            msb=msb,
            lsb=lsb,
            access=access_value,
            reset=reset,
            description=description_value,
        )

    return [], FieldDraft(
        row_number=row_number,
        name=field_name,
        msb=msb,
        lsb=lsb,
        access=access_value.lower(),
        reset=reset,
        description=description_value,
    )


def _normalize_row(columns: list[str], row: list[str]) -> dict[str, str]:
    padded = list(row)
    if len(padded) < len(columns):
        padded.extend([""] * (len(columns) - len(padded)))
    values = dict(zip(columns, padded[: len(columns)], strict=True))
    return {column: values.get(column, "") for column in EXPECTED_COLUMNS}


def _field_description(row: dict[str, str], field_name: str) -> str:
    return row["description"].strip() or field_name


def _register_description(row: dict[str, str], register_name: str) -> str:
    return row["description"].strip() or register_name


def _shared_description(row: dict[str, str], fallback: str) -> str:
    return row["description"].strip() or fallback


def _parse_reset(
    value: str, row_number: int, subsection: str | None
) -> tuple[list[str], int]:
    try:
        return [], parse_hex_literal(value)
    except HexLiteralError:
        return [
            _table_row_error(
                subsection,
                row_number,
                "Reset must be a hexadecimal literal (for example 0x0).",
            )
        ], 0
