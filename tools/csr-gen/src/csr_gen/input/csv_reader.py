"""Read CSR register models from CSV tables."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

from csr_gen.errors import CsrGenError, CsrValidationError
from csr_gen.input.table_reader import (
    TableParseError,
    parse_csr_table,
    rows_to_register_model,
)
from csr_gen.model import RegisterModel


@dataclass
class CsvRegisterSpec:
    """A register model parsed from a CSV CSR table."""

    model: RegisterModel
    section_heading: str
    heading_level: int = 2


class CsvParseError(CsrGenError):
    """Raised when a CSV CSR table cannot be parsed."""


def _resolve_csr_name(path: Path, csr_name: str | None) -> str:
    if csr_name is not None and csr_name.strip():
        return csr_name.strip()
    return path.stem


def load_csv_file(path: Path, csr_name: str | None = None) -> CsvRegisterSpec:
    """Read and validate a CSR table from a CSV file."""
    location = f"CSV file {path.name!r}"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise CsvParseError(f"Cannot read CSV file {path!r}: {error}") from error
    return load_csv(text, location=location, csr_name=_resolve_csr_name(path, csr_name))


def load_csv(
    text: str,
    *,
    location: str = "<string>",
    csr_name: str,
) -> CsvRegisterSpec:
    """Read and validate a CSR table from CSV text."""
    try:
        rows = list(csv.reader(io.StringIO(text), strict=True))
    except csv.Error as error:
        raise CsvParseError(f"{location}: malformed CSV: {error}") from error

    if not rows:
        raise CsvParseError(f"{location} is empty.")

    header_width = len(rows[0])
    header = [cell.strip() for cell in rows[0]]
    body: list[list[str]] = []
    for line_number, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) > header_width:
            raise CsvParseError(
                f"{location}: row {line_number} has {len(row)} cells; "
                f"header has {header_width}."
            )
        body.append([cell.strip() for cell in row])

    try:
        normalized, has_reset_column = parse_csr_table(header, body, location=location)
    except TableParseError as error:
        raise CsvParseError(str(error)) from error
    # Row numbers in errors match spreadsheet line numbers (row 1 = header).
    model = rows_to_register_model(
        normalized,
        has_reset_column=has_reset_column,
        first_row_number=2,
    )

    return CsvRegisterSpec(model=model, section_heading=csr_name)
