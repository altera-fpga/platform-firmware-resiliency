"""Unit tests for synthesizable SystemVerilog test harness generation."""

from pathlib import Path

import pytest

from csr_gen.input.markdown_reader import load_markdown_file
from csr_gen.model import Field, Register, RegisterModel
from csr_gen.output.synth_test_harness_writer import (
    SYNTH_HARNESS_MODULE_NAME,
    SynthTestHarnessGenerationError,
    _field_stimulus_lines,
    _observability_block,
    write_synth_test_harness_sv,
)

_GOLDEN = Path(__file__).resolve().parents[2] / "specs" / "golden" / "example-device"
_EXTERNAL_GOLDEN = (
    Path(__file__).resolve().parents[2] / "specs" / "golden" / "external-device"
)
from test_paths import TESTDATA

_CCA_ACCEL = TESTDATA / "cca_accel.md"


def test_write_synth_test_harness_sv_example_device() -> None:
    model = load_markdown_file(_GOLDEN / "regs.md", "CSR Registers").model
    text = write_synth_test_harness_sv(model, section_heading="CSR Registers")
    assert f"module {SYNTH_HARNESS_MODULE_NAME}" in text
    assert "    // Clock and reset" in text
    assert "    // AXI4-Lite slave" in text
    assert "    // Harness observability" in text
    assert "output logic       reg_obs" in text
    assert "    // --- CTRL @ 0x00 ---" in text
    assert "    logic [2:1] ctrl_mode_q;" in text
    assert "    logic [2:1] ctrl_mode_d;" in text
    assert "assign ctrl_mode_d = lfsr_q" in text
    assert "assign ctrl_mode_d_wen = lfsr_q" in text
    assert "_drv" not in text
    assert "csr_registers dut" in text
    assert ".s_axi_awaddr(s_axi_awaddr[3:0])," in text
    assert "logic [13:0] lfsr_q" in text
    assert "assign reg_obs = ^reg_obs_vector" in text
    assert "ctrl_mode_q, ctrl_enable_q, events_pending_q" in text
    port_block = text.split("module csr_synth_harness (", 1)[1].split(");", 1)[0]
    assert "ctrl_mode_q" not in port_block
    assert "fifo_wren" not in port_block


def test_write_synth_test_harness_sv_external_device() -> None:
    model = load_markdown_file(_EXTERNAL_GOLDEN / "regs.md", "CSR Registers").model
    text = write_synth_test_harness_sv(model, section_heading="CSR Registers")
    assert f"module {SYNTH_HARNESS_MODULE_NAME}" in text
    assert "    // --- STATUS @ 0x00 ---" in text
    assert "    // --- FIFO @ 0x10 ---" in text
    assert "// External model: FIFO" in text
    assert "// External model: MEM" in text
    assert "// External model: ROM" in text
    assert "// External model: WBUF" in text
    assert "    logic        fifo_wren;" in text
    assert "    logic [31:0] mem_rdata;" in text
    assert "assign status_flag_d = lfsr_q" in text
    assert "fifo_storage" in text
    assert "mem_storage" in text
    assert "rom_storage" in text
    assert "assign mem_rdatavalid = mem_rdatavalid_r;" in text
    assert ".s_axi_awaddr(s_axi_awaddr[6:0])," in text
    assert ".s_axi_araddr(s_axi_araddr[6:0])," in text
    assert "assign rom_rdatavalid = rom_rdatavalid_r;" in text
    assert "wbuf_storage" in text
    assert "assign reg_obs = ^lfsr_q;" in text
    port_block = text.split("module csr_synth_harness (", 1)[1].split(");", 1)[0]
    assert "fifo_wren" not in port_block
    assert "status_flag_d" not in port_block


def test_write_synth_test_harness_sv_external_only_block() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="FIFO",
                address=0x10,
                hw_access="external",
                fields=[Field("DATA", 7, 0, "rw", 0)],
            )
        ]
    )
    text = write_synth_test_harness_sv(model, section_heading="CSR Registers")

    assert "logic [0:0] lfsr_q;" in text
    assert "LFSR-driven D inputs" not in text
    assert "assign reg_obs = lfsr_q[0];" in text
    assert "// External model: FIFO" in text


def test_write_synth_test_harness_sv_single_q_observability() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0x00,
                fields=[Field("EN", 0, 0, "rw", 0)],
            )
        ]
    )
    text = write_synth_test_harness_sv(model, section_heading="CSR Registers")

    assert "assign reg_obs = ctrl_en_q;" in text
    assert "reg_obs_vector" not in text


def test_write_synth_test_harness_sv_cca_accel_large_internal_map() -> None:
    model = load_markdown_file(_CCA_ACCEL, "CSR Registers").model
    text = write_synth_test_harness_sv(model, section_heading="CSR Registers")

    assert "csr_registers dut" in text
    assert "assign wpref_control_run_d = lfsr_q" in text
    assert "assign wpref_control_run_d_wen = lfsr_q" in text
    assert "assign fpga_id_major_id_d = lfsr_q" in text
    assert "assign reg_obs = ^reg_obs_vector" in text


def test_write_synth_test_harness_sv_skips_none_only_internal_register() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="GAP",
                address=0x00,
                fields=[Field("RESERVED", 31, 0, "none", 0)],
            ),
            Register(
                name="FIFO",
                address=0x10,
                hw_access="external",
                fields=[Field("DATA", 31, 0, "rw", 0)],
            ),
        ]
    )
    text = write_synth_test_harness_sv(model, section_heading="CSR Registers")

    assert "// --- GAP @ 0x00 ---" not in text
    assert "// --- FIFO @ 0x10 ---" in text


@pytest.mark.parametrize(
    ("access",),
    [
        ("ro",),
        ("wo",),
    ],
)
def test_write_synth_test_harness_sv_rejects_unsupported_external_register(
    access: str,
) -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="PORT",
                address=0x00,
                hw_access="external",
                fields=[Field("DATA", 31, 0, access, 0)],
            )
        ]
    )
    with pytest.raises(SynthTestHarnessGenerationError, match="PORT"):
        write_synth_test_harness_sv(model, section_heading="CSR Registers")


def test_field_stimulus_lines_wraps_d_wen_lfsr_index() -> None:
    lines = _field_stimulus_lines([("foo_d", "foo_d_wen", 1)], lfsr_width=1)

    assert any("assign foo_d_wen = lfsr_q[0]" in line for line in lines)


def test_observability_block_ties_reg_obs_low_without_lfsr() -> None:
    lines = _observability_block([], obs_width=0, lfsr_width=0)

    assert lines == [
        "    assign reg_obs = 1'b0;",
        "",
    ]
