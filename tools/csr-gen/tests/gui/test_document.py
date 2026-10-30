"""Headless tests for the CSR GUI document layer."""

from pathlib import Path

import pytest

from csr_gen.errors import ModelValidationError
from csr_gen.input.markdown_reader import load_markdown_file
from csr_gen.model import Field, Register, RegisterModel
from csr_gen.output.c_header_writer import write_c_header
from csr_gen.output.dml_writer import write_dml
from csr_gen.output.ipxact_writer import write_ipxact
from csr_gen.output.markdown_writer import write_markdown
from csr_gen.output.systemrdl_writer import write_systemrdl
from csr_gen.output.systemverilog_writer import write_systemverilog
from csr_gen_gui.document import DocumentController

GOLDEN = Path(__file__).resolve().parents[2] / "specs" / "golden" / "example-device"


def example_device_model() -> RegisterModel:
    """Register map matching specs/golden/example-device semantics."""
    return RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0x00,
                description="Control register",
                fields=[
                    Field(
                        name="enable",
                        msb=0,
                        lsb=0,
                        access="rw",
                        reset=0,
                        description="Control register",
                    ),
                    Field(
                        name="mode",
                        msb=2,
                        lsb=1,
                        access="rw",
                        reset=1,
                        description="Enable debug mode",
                    ),
                    Field(
                        name="rsvd",
                        msb=31,
                        lsb=3,
                        access="none",
                        reset=0,
                        description="Select mode",
                    ),
                ],
            ),
            Register(
                name="EVENTS",
                address=0x04,
                description="Event register and pending event bits",
                fields=[
                    Field(
                        name="pending",
                        msb=7,
                        lsb=0,
                        access="rw1c",
                        reset=0,
                        description="Event register and pending event bits",
                    ),
                ],
            ),
        ]
    )


def test_load_example_device_preserves_unmanaged_prose() -> None:
    controller = DocumentController()
    controller.load(GOLDEN / "regs.md")

    assert len(controller.document.banks) == 1
    assert controller.active_bank.section_heading == "CSR Registers"
    assert any("Other Section" in line for line in controller.document.suffix_lines)
    assert any("Example Device" in line for line in controller.document.preamble_lines)


def test_save_example_device_matches_golden_markdown(tmp_path: Path) -> None:
    controller = DocumentController()
    controller.load(GOLDEN / "regs.md")
    output = tmp_path / "regs.md"
    controller.save(output)

    expected_table = write_markdown(
        load_markdown_file(GOLDEN / "regs.md", "CSR Registers").model,
        "CSR Registers",
        section_heading="CSR Registers",
        heading_level=2,
    )
    saved_text = output.read_text(encoding="utf-8")
    assert expected_table in saved_text
    assert "# Other Section" in saved_text


def test_new_document_multi_bank_round_trip(tmp_path: Path) -> None:
    controller = DocumentController()
    controller.new_document(document_title="Chip CSRs")
    controller.add_bank("CSR Registers")
    controller.active_bank.model = example_device_model()
    controller.add_bank("Status Block")
    controller.document.banks[1].model = RegisterModel(
        registers=[
            Register(
                name="STATUS",
                address=0x00,
                description="Status",
                fields=[
                    Field(
                        name="READY",
                        msb=0,
                        lsb=0,
                        access="ro",
                        reset=0,
                        description="Ready",
                    ),
                ],
            ),
        ]
    )

    path = tmp_path / "multi.md"
    controller.save(path)

    reloaded = DocumentController()
    reloaded.load(path)
    assert len(reloaded.document.banks) == 2
    assert reloaded.document.banks[0].section_heading == "CSR Registers"
    assert reloaded.document.banks[1].section_heading == "Status Block"
    assert len(reloaded.document.banks[0].model.registers) == 2
    assert reloaded.document.banks[1].model.registers[0].name == "STATUS"


def test_generate_previews_match_golden_oracles() -> None:
    controller = DocumentController()
    controller.add_bank("CSR Registers")
    controller.active_bank.model = example_device_model()

    previews = controller.generate_previews()
    assert previews.errors == []

    assert previews.systemverilog == write_systemverilog(
        controller.active_bank.model,
        "axi4-lite",
        section_heading="CSR Registers",
    )
    assert previews.c_header == write_c_header(
        controller.active_bank.model,
        section_heading="CSR Registers",
    )
    assert previews.dml == write_dml(
        controller.active_bank.model,
        section_heading="CSR Registers",
    )
    assert previews.systemrdl == write_systemrdl(
        controller.active_bank.model,
        section_heading="CSR Registers",
    )
    assert previews.ipxact == write_ipxact(
        controller.active_bank.model,
        memory_map_name="CSR Registers",
    )


def test_generate_previews_report_validation_errors() -> None:
    controller = DocumentController()
    controller.add_bank("CSR Registers")
    controller.active_bank.model = RegisterModel(
        registers=[
            Register(
                name="BAD",
                address=0x00,
                description="",
                fields=[
                    Field(
                        name="A",
                        msb=4,
                        lsb=0,
                        access="rw",
                        reset=0,
                    ),
                    Field(
                        name="B",
                        msb=3,
                        lsb=0,
                        access="rw",
                        reset=0,
                    ),
                ],
            ),
        ]
    )

    previews = controller.generate_previews()
    assert previews.systemverilog is None
    assert previews.c_header is None
    assert previews.dml is None
    assert previews.systemrdl is None
    assert previews.ipxact is None
    assert previews.errors


def test_save_rejects_invalid_model(tmp_path: Path) -> None:
    controller = DocumentController()
    controller.add_bank("CSR Registers")
    path = tmp_path / "bad.md"

    with pytest.raises(ModelValidationError):
        controller.save(path)


def test_rename_and_remove_bank() -> None:
    controller = DocumentController()
    controller.add_bank("Alpha")
    controller.add_bank("Beta")
    controller.set_active_bank(1)
    controller.rename_bank(1, "Status Block")
    assert controller.active_bank.section_heading == "Status Block"

    controller.remove_bank(0)
    assert len(controller.document.banks) == 1
    assert controller.active_bank.section_heading == "Status Block"
