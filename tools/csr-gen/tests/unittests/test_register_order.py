"""Tests for canonical register and field ordering in serializers."""

import csv
import io

from csr_gen.model import Field, Register, RegisterModel
from csr_gen.output.csv_writer import write_csv
from csr_gen.output.ipxact_writer import write_ipxact
from csr_gen.output.markdown_writer import write_markdown
from csr_gen.output.register_order import sorted_fields, sorted_registers
from csr_gen.output.systemrdl_writer import write_systemrdl


def _out_of_order_model() -> RegisterModel:
    return RegisterModel(
        registers=[
            Register(
                name="HIGH",
                address=0x10,
                description="High register",
                fields=[
                    Field(
                        name="TOP",
                        msb=31,
                        lsb=16,
                        access="rw",
                        reset=0,
                        description="Top half",
                    ),
                    Field(
                        name="BOT",
                        msb=7,
                        lsb=0,
                        access="rw",
                        reset=0,
                        description="Bottom byte",
                    ),
                ],
            ),
            Register(
                name="LOW",
                address=0x0,
                description="Low register",
                fields=[
                    Field(
                        name="FLAG",
                        msb=0,
                        lsb=0,
                        access="rw",
                        reset=0,
                        description="Flag",
                    ),
                ],
            ),
        ]
    )


def test_sorted_registers_and_fields_helpers() -> None:
    model = _out_of_order_model()
    assert [register.name for register in sorted_registers(model)] == ["LOW", "HIGH"]
    high = next(register for register in model.registers if register.name == "HIGH")
    assert [field.name for field in sorted_fields(high)] == ["BOT", "TOP"]


def _markdown_register_names(markdown: str) -> list[str]:
    names: list[str] = []
    for line in markdown.splitlines():
        if not line.startswith("| ") or line.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if cells[0] in {"", "Register"}:
            continue
        names.append(cells[0])
    return names


def _markdown_field_names_for_register(markdown: str, register_name: str) -> list[str]:
    fields: list[str] = []
    in_register = False
    for line in markdown.splitlines():
        if not line.startswith("| ") or line.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if cells[0] == register_name:
            in_register = True
            continue
        if in_register and cells[0]:
            break
        if in_register and cells[2]:
            fields.append(cells[2])
    return fields


def test_markdown_writer_sorts_registers_and_fields() -> None:
    markdown = write_markdown(_out_of_order_model(), "CSR Registers")
    assert _markdown_register_names(markdown) == ["LOW", "HIGH"]
    assert _markdown_field_names_for_register(markdown, "HIGH") == ["BOT", "TOP"]


def test_csv_writer_sorts_registers_and_fields() -> None:
    reader = csv.reader(io.StringIO(write_csv(_out_of_order_model())))
    rows = list(reader)[1:]
    register_names = [row[0] for row in rows if row[0]]
    assert register_names == ["LOW", "HIGH"]
    high_field_rows = [row[2] for row in rows if not row[0] and row[2]][-2:]
    assert high_field_rows == ["BOT", "TOP"]


def test_ipxact_writer_sorts_registers_and_fields() -> None:
    xml = write_ipxact(_out_of_order_model(), memory_map_name="CSR Registers")
    low_offset = xml.index("<ipxact:name>LOW</ipxact:name>")
    high_offset = xml.index("<ipxact:name>HIGH</ipxact:name>")
    assert low_offset < high_offset

    high_section = xml[high_offset:]
    bot_offset = high_section.index("<ipxact:name>BOT</ipxact:name>")
    top_offset = high_section.index("<ipxact:name>TOP</ipxact:name>")
    assert bot_offset < top_offset


def test_systemrdl_writer_sorts_registers_and_fields() -> None:
    rdl = write_systemrdl(_out_of_order_model(), section_heading="CSR Registers")
    low_offset = rdl.index("LOW @ 0x0")
    high_offset = rdl.index("HIGH @ 0x10")
    assert low_offset < high_offset

    bot_offset = rdl.index("BOT[7:0]")
    top_offset = rdl.index("TOP[31:16]")
    assert bot_offset < top_offset
    assert bot_offset < high_offset
