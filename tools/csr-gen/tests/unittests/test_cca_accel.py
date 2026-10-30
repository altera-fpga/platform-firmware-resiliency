"""Unit tests for tests/testdata/cca_accel.md."""

from test_paths import TESTDATA

from csr_gen.input.markdown_reader import load_markdown_file
from csr_gen.output.c_header_writer import write_c_header
from csr_gen.output.systemverilog_writer import (
    module_name_from_section,
    write_systemverilog,
)

CCA_ACCEL_MD = TESTDATA / "cca_accel.md"
CSR_SECTION = "CSR Registers"
DMA_SECTION = "DMA Registers"
ACCEL_SECTION = "Accelerator CSR Block"


def test_cca_accel_dma_registers_merges_subsections() -> None:
    spec = load_markdown_file(CCA_ACCEL_MD, DMA_SECTION)

    assert spec.section_heading == DMA_SECTION
    names = [register.name for register in spec.model.registers]
    assert names[:4] == [
        "WPREF_CONTROL",
        "WPREF_NEXT_DESC_LOW",
        "WPREF_NEXT_DESC_HI",
        "WPREF_RESERVED_0C",
    ]
    assert "RPREF_CONTROL" in names
    assert "WDISP_STATUS" in names
    assert "RDISP_SEQUENCE_NUMBER" in names
    assert len(names) == 32
    assert spec.model.registers[0].address == 0x3020_4000
    assert spec.model.registers[-1].address == 0x3020_407C


def test_cca_accel_csr_registers_merges_dma_and_accelerator() -> None:
    spec = load_markdown_file(CCA_ACCEL_MD, CSR_SECTION)

    assert spec.section_heading == CSR_SECTION
    names = [register.name for register in spec.model.registers]
    assert names[0] == "WPREF_CONTROL"
    assert names[31] == "RDISP_RESERVED_1C"
    assert names[32] == "FPGA_ID"
    assert names[-1] == "ACCEL_DBG_10_REG_DATA"
    assert len(names) == 52
    assert spec.model.registers[0].address == 0x3020_4000
    assert spec.model.registers[-1].address == 0x3040_006C


def test_cca_accel_wpref_status_has_rw1c_field() -> None:
    spec = load_markdown_file(CCA_ACCEL_MD, DMA_SECTION)
    status = next(r for r in spec.model.registers if r.name == "WPREF_STATUS")
    irq = next(f for f in status.fields if f.name == "IRQ")
    assert irq.access == "rw1c"
    assert irq.lsb == 0


def test_cca_accel_wdisp_status_reset_idle_bit() -> None:
    spec = load_markdown_file(CCA_ACCEL_MD, DMA_SECTION)
    status = next(r for r in spec.model.registers if r.name == "WDISP_STATUS")
    idle = next(f for f in status.fields if f.name == "STOPPED_IDLE")
    assert idle.reset == 1
    assert idle.access == "ro"


def test_cca_accel_accelerator_block_registers() -> None:
    spec = load_markdown_file(CCA_ACCEL_MD, ACCEL_SECTION)

    assert spec.section_heading == ACCEL_SECTION
    names = [register.name for register in spec.model.registers]
    assert names[0] == "FPGA_ID"
    assert "ACCEL_CONTROL" in names
    assert "ACCEL_DBG_10_REG_DATA" in names
    assert len(names) == 20
    assert spec.model.registers[0].address == 0x3040_0000


def test_cca_accel_fpga_id_field_resets() -> None:
    spec = load_markdown_file(CCA_ACCEL_MD, ACCEL_SECTION)
    fpga_id = spec.model.registers[0]
    variant = next(f for f in fpga_id.fields if f.name == "VARIANT_ID")
    major = next(f for f in fpga_id.fields if f.name == "MAJOR_ID")
    assert variant.reset == 0x03
    assert major.reset == 0x01


def test_cca_accel_write_systemverilog_accelerator_module() -> None:
    spec = load_markdown_file(CCA_ACCEL_MD, ACCEL_SECTION)
    rtl = write_systemverilog(spec.model, "axi4-lite", section_heading=ACCEL_SECTION)

    assert module_name_from_section(ACCEL_SECTION) == "accelerator_csr_block"
    assert "module accelerator_csr_block" in rtl
    assert "FPGA_ID_ADDR = 30'h30400000" in rtl
    assert "accel_control_cmd_q" in rtl
    assert "fpga_id_major_id_d" in rtl


def test_cca_accel_write_c_header_accel_control_reset() -> None:
    spec = load_markdown_file(CCA_ACCEL_MD, ACCEL_SECTION)
    header = write_c_header(spec.model, section_heading=ACCEL_SECTION)

    assert "ACCELERATOR_CSR_BLOCK_ACCEL_CONTROL_RESET 0x00008000u" in header
    assert "ACCELERATOR_CSR_BLOCK_FPGA_ID_RESET 0x01010003u" in header
