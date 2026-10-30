"""Serialize CSR register models to Markdown register tables."""

from pathlib import Path

from csr_gen.model import DEFAULT_HW_ACCESS, Field, Register, RegisterModel
from csr_gen.output.register_order import sorted_fields, sorted_registers

DEFAULT_ACCESS = "rw"

MARKDOWN_COLUMNS = (
    "Register",
    "Address",
    "Field",
    "Bits",
    "Access",
    "Reset",
    "HW Access",
    "Description",
)


def write_markdown_file(
    path: Path,
    model: RegisterModel,
    section: str,
    *,
    section_heading: str | None = None,
    heading_level: int | None = None,
) -> None:
    """Write a Markdown CSR specification to a file."""
    path.write_text(
        write_markdown(
            model,
            section,
            section_heading=section_heading,
            heading_level=heading_level,
        ),
        encoding="utf-8",
    )


def write_markdown(
    model: RegisterModel,
    section: str,
    *,
    section_heading: str | None = None,
    heading_level: int | None = None,
) -> str:
    """Render a register model as a Markdown document with one CSR table section."""
    title = section_heading.strip() if section_heading is not None else section.strip()
    level = heading_level if heading_level is not None else 2
    heading = f"{'#' * level} {title}"
    lines = [heading, "", _table_header(), _table_separator()]
    for register in sorted_registers(model):
        lines.extend(_register_rows(register))
    return "\n".join(lines) + "\n"


def _table_header() -> str:
    return "| " + " | ".join(MARKDOWN_COLUMNS) + " |"


def _table_separator() -> str:
    return "| " + " | ".join("---" for _ in MARKDOWN_COLUMNS) + " |"


def _register_rows(register: Register) -> list[str]:
    rows: list[str] = []
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
) -> str:
    cells = [
        _escape_cell(register),
        _escape_cell(address),
        _escape_cell(field),
        _escape_cell(bits),
        _escape_cell(access),
        _escape_cell(reset),
        _escape_cell(hw_access),
        _escape_cell(description),
    ]
    return "| " + " | ".join(cells) + " |"


def _escape_cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|").strip()


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
