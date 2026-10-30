from pathlib import Path

import pytest

from csr_gen.errors import CsrValidationError, MarkdownParseError
from csr_gen.input.markdown_reader import load_markdown, load_markdown_file

from test_paths import TESTDATA

HEADER = """\
| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
"""


def _document(*rows: str, heading: str = "# Registers", header: str = HEADER) -> str:
    return f"{heading}\n\n{header}{chr(10).join(rows)}\n"


HEADER_MINIMAL = """\
| Register | Address | Field | Bits | Reset |
| --- | --- | --- | --- | --- |
"""

HEADER_NO_RESET = """\
| Register | Address | Field | Bits |
| --- | --- | --- | --- |
"""


def test_load_markdown_from_memory_normalizes_model() -> None:
    spec = load_markdown(
        _document(
            "| ctrl | 0x00 | enable | 0 | rw | 0x0 | Control and **enable** |",
            "|  |  | mode | 2:1 | ro | 0x1 | Select `<b>mode</b>` |",
        ),
        "registers",
    )

    assert len(spec.model.registers) == 1
    register = spec.model.registers[0]
    assert register.name == "CTRL"
    assert register.address == 0
    assert register.description == "Control and enable"
    assert [field.name for field in register.fields] == ["ENABLE", "MODE"]
    assert register.fields[0].description == "Control and enable"
    assert register.fields[1].description == "Select mode"
    assert (register.fields[1].msb, register.fields[1].lsb) == (2, 1)


def test_load_markdown_accepts_register_definition_rows() -> None:
    spec = load_markdown(
        _document(
            "| CTRL | 0x00 |  |  |  |  | Control register |",
            "|  |  | enable | 0 | rw | 0x0 | Enable path |",
            "|  |  | mode | 2:1 | rw | 0x1 | |",
        ),
        "Registers",
    )

    register = spec.model.registers[0]
    assert register.name == "CTRL"
    assert register.description == "Control register"
    assert register.fields[0].name == "ENABLE"
    assert register.fields[0].description == "Enable path"
    assert register.fields[1].name == "MODE"
    assert register.fields[1].description == "mode"


def test_load_markdown_rejects_hw_access_on_field_row() -> None:
    with pytest.raises(CsrValidationError, match="register definition row"):
        load_markdown(
            _document(
                "| CTRL | 0x00 |  |  |  |  | | internal |",
                "|  |  | enable | 0 | rw | 0 | | external |",
                header="""\
| Register | Address | Field | Bits | Access | Reset | Description | HW Access |
| --- | --- | --- | --- | --- | --- | --- | --- |
""",
            ),
            "Registers",
        )


def test_load_markdown_accepts_table_without_optional_columns() -> None:
    spec = load_markdown(
        _document(
            "| CTRL | 0x00 | enable | 0 | 0x0 |",
            "|  |  | mode | 2:1 | 0x1 |",
            header=HEADER_MINIMAL,
        ),
        "Registers",
    )

    register = spec.model.registers[0]
    assert register.description == "enable"
    assert register.fields[0].access == "rw"
    assert register.fields[0].description == "enable"
    assert register.fields[1].access == "rw"
    assert register.fields[1].description == "mode"


def test_load_markdown_defaults_empty_access_and_description_cells() -> None:
    spec = load_markdown_file(
        TESTDATA / "optional_access_and_description_cells.md",
        "CSR Registers",
    )

    register = spec.model.registers[0]
    assert register.description == "enable"
    assert register.fields[0].access == "rw"
    assert register.fields[0].description == "enable"
    assert register.fields[1].access == "ro"
    assert register.fields[1].description == "Explicit mode text"


def test_load_markdown_defaults_reset_when_column_omitted() -> None:
    spec = load_markdown_file(
        TESTDATA / "optional_no_reset_column.md",
        "CSR Registers",
    )

    register = spec.model.registers[0]
    assert all(field.reset == 0 for field in register.fields)


def test_load_markdown_defaults_reset_when_column_omitted_from_memory() -> None:
    spec = load_markdown(
        _document(
            "| CTRL | 0x00 | enable | 0 |",
            "|  |  | mode | 2:1 |",
            header=HEADER_NO_RESET,
        ),
        "Registers",
    )

    register = spec.model.registers[0]
    assert register.fields[0].reset == 0
    assert register.fields[1].reset == 0


def test_load_markdown_file_accepts_reordered_columns_without_optional_columns() -> (
    None
):
    spec = load_markdown_file(
        TESTDATA / "optional_columns_reordered.md",
        "CSR Registers",
    )

    assert [register.name for register in spec.model.registers] == ["CTRL", "EVENTS"]
    assert spec.model.registers[0].fields[0].description == "enable"
    assert spec.model.registers[0].fields[0].access == "rw"
    assert spec.model.registers[1].fields[0].description == "pending"


def test_load_markdown_file_accepts_reordered_columns_and_complex_document() -> None:
    spec = load_markdown_file(TESTDATA / "valid_registers.md", "csr registers")

    assert [register.name for register in spec.model.registers] == ["CTRL", "EVENTS"]
    assert [field.name for field in spec.model.registers[0].fields] == [
        "ENABLE",
        "MODE",
    ]
    assert spec.model.registers[0].fields[1].description == "Enable debug mode"


def test_load_markdown_merges_tables_from_subsections() -> None:
    spec = load_markdown_file(
        TESTDATA / "multi_subsection_tables.md",
        "CSR Registers",
    )

    assert [register.name for register in spec.model.registers] == ["CTRL", "EVENTS"]
    assert spec.model.registers[0].address == 0
    assert spec.model.registers[1].address == 4


def test_load_markdown_rejects_duplicate_address_across_subsections() -> None:
    markdown = """\
# Registers

## CSR Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x00 | enable | 0 | rw | 0 | Enable |

### Other bank

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| STATUS | 0x00 | ready | 0 | ro | 0 | Ready |
"""
    with pytest.raises(CsrValidationError, match="overlaps"):
        load_markdown(markdown, "CSR Registers")


def test_load_markdown_preserves_source_section_heading() -> None:
    spec = load_markdown_file(TESTDATA / "valid_registers.md", "csr registers")

    assert spec.section_heading == "CSR Registers"
    assert spec.heading_level == 2


@pytest.mark.parametrize(
    ("fixture", "message"),
    [
        ("duplicate_section.md", "exactly one heading"),
        ("two_tables.md", "at most one CSR table"),
        ("two_tables_one_subsection.md", "at most one CSR table"),
    ],
)
def test_load_markdown_file_rejects_ambiguous_document(
    fixture: str, message: str
) -> None:
    with pytest.raises(MarkdownParseError, match=message):
        load_markdown_file(TESTDATA / fixture, "CSR Registers")


@pytest.mark.parametrize(
    ("markdown", "message"),
    [
        ("# Other\n", "exactly one heading"),
        ("# Registers\n\nNo table.\n", "at least one CSR table"),
        (
            """\
# Registers

| Register | Address |
| --- | --- |
| CTRL | 0x00 |
""",
            "missing required column",
        ),
        (
            """\
# Registers

| Register | Address | Field | Bits | Access | Reset | Description | Extra |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x00 | ENABLE | 0 | rw | 0 | | |
""",
            "unsupported column",
        ),
        (
            """\
# Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
""",
            "header and at least one row",
        ),
    ],
)
def test_load_markdown_rejects_malformed_document(markdown: str, message: str) -> None:
    with pytest.raises(MarkdownParseError, match=message):
        load_markdown(markdown, "Registers")


@pytest.mark.parametrize(
    ("markdown", "message"),
    [
        (_document("| CTRL |  | ENABLE | 0 | rw | 0 | |"), "both Register"),
        (_document("|  |  | ENABLE | 0 | rw | 0 | |"), "before one is declared"),
        (
            _document("| CTRL | 0x00 |  | 0 |  |  | |"),
            "Bits must be empty on a register definition row",
        ),
        (
            _document("| CTRL | 0x00 |  |  |  |  | |"),
            "must contain at least one field",
        ),
        (
            _document("| CTRL | 0x00 |  |  |  |  | |", "|  |  |  |  |  |  | |"),
            "register definition row or a Field",
        ),
        (_document("| CTRL | invalid | ENABLE | 0 | rw | 0 | |"), "Address"),
        (_document("| CTRL | 0x00 | ENABLE | invalid | rw | 0 | |"), "Bits"),
        (_document("| CTRL | 0x00 | ENABLE | 0 | rw | invalid | |"), "Reset"),
    ],
)
def test_load_markdown_rejects_invalid_rows(markdown: str, message: str) -> None:
    with pytest.raises(CsrValidationError, match=message):
        load_markdown(markdown, "Registers")


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        (
            (
                "| CTRL | 0x00 | ENABLE | 0 | rw | 0 | |",
                "| ctrl | 0x04 | OTHER | 1 | rw | 0 | |",
            ),
            "Duplicate register name",
        ),
        (
            (
                "| CTRL | 0x00 | ENABLE | 0 | rw | 0 | |",
                "| OTHER | 0x00 | VALUE | 1 | rw | 0 | |",
            ),
            "overlaps",
        ),
        (
            (
                "| CTRL | 0x00 | ENABLE | 0 | rw | 0 | |",
                "|  |  | enable | 1 | rw | 0 | |",
            ),
            "duplicate field name",
        ),
        (
            (
                "| CTRL | 0x00 | LOW | 3:0 | rw | 0 | |",
                "|  |  | HIGH | 4:3 | rw | 0 | |",
            ),
            "overlaps",
        ),
        (("| CTRL | 0x00 | ENABLE | 0 | invalid | 0 | |",), "unsupported access"),
        (("| CTRL | 0x00 | ENABLE | 32 | rw | 0 | |",), "32-bit"),
        (("| CTRL | 0x00 | ENABLE | 0 | rw | 0x2 | |",), "does not fit"),
        (("| CTRL | 0x02 | ENABLE | 0 | rw | 0 | |",), "4-byte aligned"),
    ],
)
def test_load_markdown_runs_model_legality(rows: tuple[str, ...], message: str) -> None:
    with pytest.raises(CsrValidationError, match=message) as error:
        load_markdown(_document(*rows), "Registers")
    assert message in error.value.messages[0]


def test_load_markdown_reports_all_invalid_rows() -> None:
    with pytest.raises(CsrValidationError) as error:
        load_markdown(
            _document(
                "| CTRL | 0x00 | LOW | 3:0 | rw | 0 | |",
                "|  |  | HIGH | 2:1 | rw | 0 | |",
                "| BAD | 0xbad! | OTHER | 0 | rw | 0 | |",
            ),
            "Registers",
        )

    messages = "\n".join(error.value.messages)
    assert "row 1" in messages
    assert "row 2" in messages
    assert "row 3" in messages
    assert "overlaps" in messages
    assert "Address must be a hexadecimal literal" in messages


HW_HEADER = """\
| Register | Address | Field | Bits | Access | Reset | Description | HW Access |
| --- | --- | --- | --- | --- | --- | --- | --- |
"""


def test_load_markdown_parses_hw_access_and_address_range() -> None:
    spec = load_markdown(
        _document(
            "| MEM | 0x20-0x2F | window | 31:0 | rw | 0 | Memory | external |",
            header=HW_HEADER,
        ),
        "Registers",
    )
    register = spec.model.registers[0]
    assert register.hw_access == "external"
    assert register.address == 0x20
    assert register.address_end == 0x2F


def test_load_markdown_defaults_hw_access_to_internal() -> None:
    spec = load_markdown(
        _document(
            "| CTRL | 0x00 | enable | 0 | rw | 0 | Control | |",
            header=HW_HEADER,
        ),
        "Registers",
    )
    assert spec.model.registers[0].hw_access == "internal"


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        (
            ("| MEM | 0x00-0x0C | window | 31:0 | rw | 0 | Memory | internal |",),
            "address range requires HW Access external",
        ),
        (
            (
                "| MEM | 0x00-0x0C | low | 15:0 | rw | 0 | Memory | external |",
                "|  |  | high | 31:16 | rw | 0 | Memory | |",
            ),
            "address range requires exactly one field",
        ),
        (
            ("| MEM | 0x00-0x0C | window | 15:0 | rw | 0 | Memory | external |",),
            "must span bits 31:0",
        ),
    ],
)
def test_load_markdown_rejects_invalid_hw_access_and_ranges(
    rows: tuple[str, ...], message: str
) -> None:
    with pytest.raises(CsrValidationError, match=message):
        load_markdown(_document(*rows, header=HW_HEADER), "Registers")


def test_load_markdown_rejects_hw_access_on_continuation_row() -> None:
    with pytest.raises(CsrValidationError, match="register definition row"):
        load_markdown(
            _document(
                "| CTRL | 0x00 | enable | 0 | rw | 0 | Control | internal |",
                "|  |  | mode | 2:1 | rw | 0 | Mode | external |",
                header=HW_HEADER,
            ),
            "Registers",
        )


def test_load_markdown_rejects_invalid_hw_access_value() -> None:
    with pytest.raises(CsrValidationError, match="HW Access must be one of"):
        load_markdown(
            _document(
                "| CTRL | 0x00 | enable | 0 | rw | 0 | Control | bogus |",
                header=HW_HEADER,
            ),
            "Registers",
        )


def test_load_markdown_rejects_duplicate_column_names() -> None:
    markdown = """\
# Registers

| Register | Register | Field | Bits | Reset |
| --- | --- | --- | --- | --- |
| CTRL | 0x00 | ENABLE | 0 | 0 |
"""
    with pytest.raises(MarkdownParseError, match="duplicate column names"):
        load_markdown(markdown, "Registers")


@pytest.mark.parametrize(
    ("address", "message"),
    [
        ("0x20-0x10", "must be >="),
        ("0x20-0x22", "valid inclusive last byte"),
        ("0x20-0x26", "valid inclusive last byte"),
    ],
)
def test_load_markdown_rejects_invalid_address_ranges(
    address: str, message: str
) -> None:
    with pytest.raises(CsrValidationError, match=message):
        load_markdown(
            _document(
                f"| MEM | {address} | window | 31:0 | rw | 0 | Memory | external |",
                header=HW_HEADER,
            ),
            "Registers",
        )


def _optional_column_table(
    optional_set: str, *, reordered: bool
) -> tuple[str, tuple[str, ...]]:
    """Build header and rows for optional-column acceptance cases."""
    columns_by_set = {
        "none": ["Register", "Address", "Field", "Bits"],
        "access_only": ["Register", "Address", "Field", "Bits", "Access", "Reset"],
        "description_only": [
            "Register",
            "Address",
            "Field",
            "Bits",
            "Reset",
            "Description",
        ],
        "hw_access_only": [
            "Register",
            "Address",
            "Field",
            "Bits",
            "Reset",
            "HW Access",
        ],
        "all_three": [
            "Register",
            "Address",
            "Field",
            "Bits",
            "Access",
            "Reset",
            "Description",
            "HW Access",
        ],
    }
    columns = columns_by_set[optional_set]
    if reordered:
        columns = list(reversed(columns))

    def _row(values: dict[str, str]) -> str:
        return "| " + " | ".join(values[column] for column in columns) + " |"

    header = (
        "| " + " | ".join(columns) + " |\n"
        "| " + " | ".join("---" for _ in columns) + " |\n"
    )
    base = {
        "Register": "CTRL",
        "Address": "0x00",
        "Field": "enable",
        "Bits": "0",
        "Access": "ro",
        "Reset": "0",
        "Description": "Control enable",
        "HW Access": "external",
    }
    continuation = {
        "Register": "",
        "Address": "",
        "Field": "mode",
        "Bits": "2:1",
        "Access": "",
        "Reset": "1",
        "Description": "",
        "HW Access": "",
    }
    if optional_set == "none":
        base.pop("Access", None)
        base.pop("Description", None)
        base.pop("HW Access", None)
        base.pop("Reset", None)
        continuation.pop("Access", None)
        continuation.pop("Description", None)
        continuation.pop("HW Access", None)
        continuation.pop("Reset", None)
    elif optional_set == "access_only":
        base.pop("Description", None)
        base.pop("HW Access", None)
        continuation.pop("Description", None)
        continuation.pop("HW Access", None)
    elif optional_set == "description_only":
        base.pop("Access", None)
        base.pop("HW Access", None)
        continuation.pop("Access", None)
        continuation.pop("HW Access", None)
    elif optional_set == "hw_access_only":
        base.pop("Access", None)
        base.pop("Description", None)
        continuation.pop("Access", None)
        continuation.pop("Description", None)
    return header, (_row(base), _row(continuation))


@pytest.mark.parametrize(
    "optional_set",
    ["none", "access_only", "description_only", "hw_access_only", "all_three"],
)
@pytest.mark.parametrize("reordered", [False, True])
def test_load_markdown_accepts_optional_column_patterns(
    optional_set: str, reordered: bool
) -> None:
    header, rows = _optional_column_table(optional_set, reordered=reordered)
    spec = load_markdown(_document(*rows, header=header), "Registers")

    register = spec.model.registers[0]
    assert register.name == "CTRL"
    assert [field.name for field in register.fields] == ["ENABLE", "MODE"]
    if optional_set == "none":
        assert register.fields[0].access == "rw"
        assert all(field.reset == 0 for field in register.fields)
    elif optional_set in {"description_only", "hw_access_only"}:
        assert register.fields[0].access == "rw"
        assert register.fields[0].reset == 0
        assert register.fields[1].reset == 1
    else:
        assert register.fields[0].access == "ro"
        assert register.fields[0].reset == 0
        assert register.fields[1].reset == 1
    if optional_set in {"none", "access_only", "hw_access_only"}:
        assert register.fields[0].description == "enable"
    else:
        assert register.fields[0].description == "Control enable"
    if optional_set in {"hw_access_only", "all_three"}:
        assert register.hw_access == "external"
    else:
        assert register.hw_access == "internal"


def test_load_markdown_accepts_hex_address_range_endpoints() -> None:
    spec = load_markdown(
        _document(
            "| MEM | 0x0-0xf | window | 31:0 | rw | 0 | Memory | external |",
            header=HW_HEADER,
        ),
        "Registers",
    )
    register = spec.model.registers[0]
    assert register.address == 0
    assert register.address_end == 0xF


def test_load_markdown_rejects_empty_bits() -> None:
    with pytest.raises(CsrValidationError, match="Bits must not be empty"):
        load_markdown(_document("| CTRL | 0x00 | ENABLE |  | rw | 0 | |"), "Registers")


def test_load_markdown_rejects_empty_reset_when_column_present() -> None:
    with pytest.raises(CsrValidationError, match="Reset must not be empty"):
        load_markdown(_document("| CTRL | 0x00 | ENABLE | 0 | rw |  | |"), "Registers")


def test_load_markdown_rejects_hw_access_value_on_field_row() -> None:
    with pytest.raises(CsrValidationError, match="register definition row"):
        load_markdown(
            _document(
                "| CTRL | 0x00 | enable | 0 | rw | 0 | Control | internal |",
                "|  |  | mode | 2:1 | rw | 0 | Mode | bogus |",
                header=HW_HEADER,
            ),
            "Registers",
        )


def test_load_markdown_reports_subsection_scoped_row_errors() -> None:
    markdown = """\
# Registers

## CSR Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x00 | enable | 0 | rw | 0 | Enable |

### Bank B

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| STATUS | bad! | ready | 0 | ro | 0 | Ready |
"""
    with pytest.raises(CsrValidationError) as error:
        load_markdown(markdown, "CSR Registers")

    combined = "\n".join(error.value.messages)
    assert "subsection 'Bank B' row 1" in combined
    assert "Address must be a hexadecimal literal" in combined


def test_load_markdown_rejects_unparseable_address_range_endpoints() -> None:
    with pytest.raises(
        CsrValidationError, match="Address must be a hexadecimal literal"
    ):
        load_markdown(
            _document(
                "| MEM | 0x00-0g8 | window | 31:0 | rw | 0 | Memory | external |",
                header=HW_HEADER,
            ),
            "Registers",
        )
