"""Headless tests for GUI import and export helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from csr_gen.errors import ModelValidationError
from csr_gen.input.ipxact_reader import list_ipxact_address_block_names_file
from csr_gen.input.systemrdl_reader import list_systemrdl_addrmap_instances_file
from csr_gen.model import Field, Register, RegisterModel
from csr_gen.output.csv_writer import write_csv
from csr_gen_gui.document import DocumentController
from csr_gen_gui.import_export import (
    ExportFormat,
    default_export_filename,
    export_bank_file,
    import_bank_from_csv,
    import_bank_from_ipxact,
    import_bank_from_systemrdl,
    ipxact_import_selector_names,
    systemrdl_import_selector_names,
    validate_bank_for_export,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTDATA = REPO_ROOT / "tests" / "testdata"
GOLDEN = REPO_ROOT / "specs" / "golden" / "example-device"


def example_device_model() -> RegisterModel:
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
                ],
            ),
        ]
    )


def test_ipxact_import_selector_names_for_single_block() -> None:
    names = ipxact_import_selector_names(TESTDATA / "ipxact_minimal.xml")
    assert names is None


def test_ipxact_import_selector_names_for_multi_block() -> None:
    names = ipxact_import_selector_names(TESTDATA / "ipxact_multi_block.xml")
    assert names == ["alpha_block", "beta_block"]


def test_list_ipxact_address_block_names_file() -> None:
    assert list_ipxact_address_block_names_file(
        TESTDATA / "ipxact_multi_block.xml",
    ) == ["alpha_block", "beta_block"]


def test_systemrdl_import_selector_names_for_flat_file() -> None:
    names = systemrdl_import_selector_names(TESTDATA / "systemrdl" / "native_flat.rdl")
    assert names is None


def test_systemrdl_import_selector_names_for_multi_peripheral() -> None:
    path = TESTDATA / "systemrdl" / "hierarchical_multi_peripheral.rdl"
    names = systemrdl_import_selector_names(path)
    assert names == ["uart_inst", "spi_inst"]
    assert list_systemrdl_addrmap_instances_file(path) == names


def test_import_bank_from_ipxact_and_csv(tmp_path: Path) -> None:
    bank = import_bank_from_ipxact(TESTDATA / "ipxact_minimal.xml")
    assert bank.section_heading == "Example CSR Map"
    assert len(bank.model.registers) == 3

    csv_path = tmp_path / "regs.csv"
    csv_path.write_text(
        "Register,Address,Field,Bits,Access,Reset,Description\n"
        "STAT,0x0,FLAG,0,rw,0x0,Status flag\n",
        encoding="utf-8",
    )
    csv_bank = import_bank_from_csv(csv_path, section_heading="Status Block")
    assert csv_bank.section_heading == "Status Block"
    assert csv_bank.model.registers[0].name == "STAT"


def test_import_bank_from_systemrdl_selected_instance() -> None:
    path = TESTDATA / "systemrdl" / "hierarchical_multi_peripheral.rdl"
    bank = import_bank_from_systemrdl(path, addrmap_instance="uart_inst")
    assert bank.section_heading == "UART"
    assert bank.model.registers[0].name == "UART_TX"


def test_document_controller_import_bank_replaces_document() -> None:
    controller = DocumentController()
    controller.load(GOLDEN / "regs.md")
    assert controller.document.source_path == GOLDEN / "regs.md"
    assert len(controller.document.banks) == 1

    bank = import_bank_from_ipxact(TESTDATA / "ipxact_minimal.xml")
    index = controller.import_bank(bank)

    assert index == 0
    assert len(controller.document.banks) == 1
    assert controller.active_bank.section_heading == "Example CSR Map"
    assert controller.document.source_path is None
    assert controller.document.preamble_lines == []
    assert controller.document.suffix_lines == []


def test_import_bank_replaces_document_and_save_succeeds(tmp_path: Path) -> None:
    controller = DocumentController()
    controller.new_document()
    controller.add_bank("CSR Registers")

    bank = import_bank_from_ipxact(TESTDATA / "ipxact_minimal.xml")
    index = controller.import_bank(bank)

    assert index == 0
    assert len(controller.document.banks) == 1
    assert controller.active_bank.section_heading == "Example CSR Map"

    path = tmp_path / "imported.md"
    controller.save(path)
    assert path.is_file()


def test_export_bank_file_writes_csv(tmp_path: Path) -> None:
    from csr_gen_gui.models import Bank

    bank = Bank(section_heading="CSR Registers", model=example_device_model())
    output = tmp_path / "regs.csv"
    export_bank_file(
        bank,
        output,
        ExportFormat.CSV,
        interface_type="axi4-lite",
    )
    assert output.read_text(encoding="utf-8") == write_csv(bank.model)


def test_default_export_filename_uses_section_heading() -> None:
    assert default_export_filename("CSR Registers", ExportFormat.IPXACT) == (
        "csr_registers.xml"
    )


def test_validate_bank_for_export_rejects_overlapping_fields() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="BAD",
                address=0,
                fields=[
                    Field(name="A", msb=4, lsb=0, access="rw", reset=0),
                    Field(name="B", msb=3, lsb=0, access="rw", reset=0),
                ],
            ),
        ]
    )
    assert validate_bank_for_export(model)


def test_export_bank_file_rejects_invalid_model(tmp_path: Path) -> None:
    from csr_gen_gui.models import Bank

    bank = Bank(
        section_heading="CSR Registers",
        model=RegisterModel(
            registers=[
                Register(
                    name="BAD",
                    address=0,
                    fields=[
                        Field(name="A", msb=4, lsb=0, access="rw", reset=0),
                        Field(name="B", msb=3, lsb=0, access="rw", reset=0),
                    ],
                ),
            ]
        ),
    )
    with pytest.raises(ModelValidationError):
        export_bank_file(
            bank,
            tmp_path / "bad.csv",
            ExportFormat.CSV,
            interface_type="axi4-lite",
        )
