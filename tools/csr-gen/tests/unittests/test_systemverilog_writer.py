"""Tests for AXI4-Lite SystemVerilog generation."""

from pathlib import Path

import pytest

from csr_gen.input.markdown_reader import load_markdown_file
from csr_gen.input.yaml_reader import load_yaml_file
from csr_gen.output.systemverilog_writer import (
    RtlGenerationError,
    _external_read_needs_wait_expr,
    _external_rdatavalid_hit_terms,
    _field_axi_write_update,
    _field_read_expr,
    _register_read_always_comb,
    _response_logic,
    module_name_from_section,
    write_systemverilog,
    write_systemverilog_file,
)
from csr_gen.model import (
    Field,
    Register,
    RegisterModel,
    register_decoder_addr_width,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_CASE = REPO_ROOT / "specs" / "golden" / "example-device"


def _golden_section() -> str:
    return (GOLDEN_CASE / "section.txt").read_text(encoding="utf-8").strip()


def test_golden_yaml_export_matches_expected_sv() -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    expected = (GOLDEN_CASE / "expected.sv").read_text(encoding="utf-8")
    assert (
        write_systemverilog(model, "axi4-lite", section_heading=_golden_section())
        == expected
    )


def test_golden_regs_markdown_export_matches_expected_sv() -> None:
    section = _golden_section()
    model = load_markdown_file(GOLDEN_CASE / "regs.md", section).model
    expected = (GOLDEN_CASE / "expected.sv").read_text(encoding="utf-8")
    assert write_systemverilog(model, "axi4-lite", section_heading=section) == expected


def test_module_name_from_section_heading() -> None:
    assert module_name_from_section("CSR Registers") == "csr_registers"


def test_write_systemverilog_requires_section_heading() -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    with pytest.raises(RtlGenerationError, match="section heading"):
        write_systemverilog(model, "axi4-lite", section_heading="   ")


def test_write_systemverilog_rejects_unsupported_interface() -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    with pytest.raises(RtlGenerationError, match="apb"):
        write_systemverilog(model, "apb", section_heading=_golden_section())


def test_write_systemverilog_rejects_avalon_interface() -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    with pytest.raises(RtlGenerationError, match="avalon-mm"):
        write_systemverilog(model, "avalon-mm", section_heading=_golden_section())


def test_write_systemverilog_rejects_unknown_interface() -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    with pytest.raises(RtlGenerationError, match="Unsupported"):
        write_systemverilog(model, "wishbone", section_heading=_golden_section())


def test_write_systemverilog_includes_ascii_register_map() -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    rtl = write_systemverilog(model, "axi4-lite", section_heading=_golden_section())
    assert "// Register map" in rtl
    assert "// | CTRL     | 0x00    |" in rtl
    assert "// --- CTRL @ 0x00 ---" in rtl
    assert "// | ENABLE | 0    | rw     |" in rtl
    assert "// | RSVD   | 31:3 | none   |" in rtl
    for line in rtl.splitlines():
        if line.startswith("// |") or line.startswith("// +"):
            assert len(line) <= 80, line


def test_write_systemverilog_uses_per_register_always_blocks() -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    rtl = write_systemverilog(model, "axi4-lite", section_heading=_golden_section())
    assert rtl.count("always_ff @(posedge clk)") == 3
    assert rtl.count("always_comb begin") == 3
    assert "ctrl_read_data" in rtl
    assert "ctrl_read_ok" in rtl
    assert "// Read response mux" in rtl
    assert "// AXI4-Lite interface" in rtl
    assert "// Register update" not in rtl


def test_write_systemverilog_includes_reset_and_access_logic() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0,
                fields=[
                    Field("EN", 0, 0, "rw", 1),
                    Field("FLAG", 1, 1, "rw1c", 0),
                    Field("STAT", 2, 2, "rc", 0),
                    Field("CMD", 3, 3, "wo", 0),
                ],
            )
        ]
    )
    rtl = write_systemverilog(model, "axi4-lite", section_heading="Control Block")

    assert "module control_block" in rtl
    assert "ctrl_en_q" in rtl
    assert "ctrl_en_d" in rtl
    assert "ctrl_cmd_q" in rtl
    assert "ctrl_cmd_d" not in rtl
    assert "ctrl_stat_d" in rtl
    assert "ctrl_stat_q" not in rtl
    assert "ctrl_en_q_upd" in rtl
    assert "ctrl_en_d_wen" in rtl
    assert "CTRL_ADDR" in rtl
    assert "CTRL_RST = 32'h00000001" in rtl
    assert "if (s_axi_wstrb[0]) ctrl_q[0:0] <= s_axi_wdata[0:0]" in rtl
    assert "ctrl_q[1:1] <= ctrl_q[1:1] & ~s_axi_wdata[1:1]" in rtl
    assert "read_data[2:2] = ctrl_q[2:2]" in rtl
    assert "read_data[0:0] = ctrl_q[0:0]" in rtl
    assert "if (ctrl_en_d_wen) begin" in rtl
    assert "ctrl_q[0:0] <= ctrl_en_d;" in rtl
    assert "ctrl_en_q_upd <= ctrl_en_q_upd_pend" in rtl
    assert "if (read_en && read_hit_ctrl) begin" in rtl
    assert "if (!ctrl_stat_d_wen) begin" in rtl
    assert "ctrl_q[2:2] <= 1'b0;" in rtl


def test_field_ports_follow_register_and_msb_order() -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    rtl = write_systemverilog(model, "axi4-lite", section_heading=_golden_section())
    field_section = rtl.split("// Register interfaces")[1].split(");")[0]
    assert "ctrl_rsvd" not in field_section
    assert field_section.index("ctrl_mode_q") < field_section.index("ctrl_mode_q_upd")
    assert field_section.index("ctrl_mode_q_upd") < field_section.index("ctrl_mode_d")
    assert field_section.index("ctrl_mode_d") < field_section.index("ctrl_mode_d_wen")
    assert field_section.index("ctrl_enable_q") < field_section.index(
        "events_pending_q"
    )


def test_write_systemverilog_hw_only_register_uses_input_updates() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="STAT",
                address=0x08,
                fields=[Field("FLAG", 0, 0, "ro", 0)],
            )
        ]
    )
    rtl = write_systemverilog(model, "axi4-lite", section_heading="Status")
    assert "if (stat_flag_d_wen) begin" in rtl
    assert "stat_q[0:0] <= stat_flag_d;" in rtl
    assert "stat_flag_q_upd" not in rtl
    assert "if (write_en && hit_stat)" not in rtl


def test_axi_address_ports_sized_from_map_span() -> None:
    small = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0x0,
                fields=[Field("EN", 0, 0, "rw", 0)],
            )
        ]
    )
    small_width = register_decoder_addr_width(small)
    small_rtl = write_systemverilog(small, "axi4-lite", section_heading="Small Map")
    assert f"input  wire [{small_width - 1}:0] s_axi_awaddr" in small_rtl
    assert f"input  wire [{small_width - 1}:0] s_axi_araddr" in small_rtl
    assert f"logic [{small_width - 1}:0] s_axi_awaddr_r" in small_rtl
    assert "input  wire [31:0] s_axi_awaddr" not in small_rtl
    assert "parameter logic [31:0] BASE_ADDR" in small_rtl

    tall = RegisterModel(
        registers=[
            Register(
                name="CONFIG",
                address=0x8000,
                address_end=0x15FFFF,
                hw_access="external",
                fields=[Field("WINDOW", 31, 0, "rw", 0)],
            )
        ]
    )
    tall_width = register_decoder_addr_width(tall)
    assert tall_width >= 21
    tall_rtl = write_systemverilog(tall, "axi4-lite", section_heading="Tall Map")
    assert f"input  wire [{tall_width - 1}:0] s_axi_awaddr" in tall_rtl
    assert f"logic [{tall_width - 1}:0] s_axi_araddr_r" in tall_rtl
    pad = 32 - tall_width
    assert f"{{{{{pad}{{1'b0}}}}, s_axi_awaddr_r}} - BASE_ADDR" in tall_rtl


def test_zero_extend_to_32_passthrough_at_full_width() -> None:
    from csr_gen.output.systemverilog_writer import _zero_extend_to_32

    assert _zero_extend_to_32("s_axi_awaddr_r", 32) == "s_axi_awaddr_r"
    assert _zero_extend_to_32("s_axi_awaddr_r", 40) == "s_axi_awaddr_r"


def test_golden_external_device_matches_expected_sv() -> None:
    external_case = REPO_ROOT / "specs" / "golden" / "external-device"
    section = (external_case / "section.txt").read_text(encoding="utf-8").strip()
    model = load_markdown_file(external_case / "regs.md", section).model
    expected = (external_case / "expected.sv").read_text(encoding="utf-8")
    assert write_systemverilog(model, "axi4-lite", section_heading=section) == expected


def test_write_systemverilog_external_register_ports() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="FIFO",
                address=0x10,
                hw_access="external",
                fields=[
                    Field("DATA", 7, 0, "rw", 0),
                    Field("LEVEL", 15, 8, "ro", 0),
                ],
            )
        ]
    )
    rtl = write_systemverilog(model, "axi4-lite", section_heading="External FIFO")
    assert "// --- FIFO @ 0x10 ---" in rtl
    fifo_comment = rtl.index("// --- FIFO @ 0x10 ---")
    assert fifo_comment < rtl.index("output logic        fifo_wren")
    assert "output logic [31:0] fifo_wdata" in rtl
    assert "output logic [ 3:0] fifo_wstrb" in rtl
    assert "output logic        fifo_rden" in rtl
    assert "input  wire [31:0] fifo_rdata" in rtl
    assert "input  wire        fifo_rdatavalid" in rtl
    assert "fifo_q" not in rtl
    assert "read_resp_ready" in rtl


def test_write_systemverilog_external_range_register_ports() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="MEM",
                address=0x20,
                address_end=0x2F,
                hw_access="external",
                fields=[Field("WINDOW", 31, 0, "rw", 0)],
            )
        ]
    )
    rtl = write_systemverilog(model, "axi4-lite", section_heading="External Mem")
    assert "MEM_ADDR_END" in rtl
    assert "output logic [1:0] mem_waddr" in rtl
    assert "output logic [1:0] mem_raddr" in rtl
    assert "mem_waddr = 2'((write_offset[OFFSET_WIDTH-1:0] - MEM_ADDR) >> 2)" in rtl
    port_block = rtl.split("// Register interfaces", 1)[1].split(");", 1)[0]
    assert port_block.index("mem_wstrb") < port_block.index("mem_waddr")
    assert port_block.index("mem_waddr") < port_block.index("mem_rden")
    assert port_block.index("mem_rdatavalid") < port_block.index("mem_raddr")


def test_write_systemverilog_external_read_only_range_ports() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="ROM",
                address=0x30,
                address_end=0x3F,
                hw_access="external",
                fields=[Field("IMAGE", 31, 0, "ro", 0)],
            )
        ]
    )
    rtl = write_systemverilog(model, "axi4-lite", section_heading="External Rom")
    assert "output logic [1:0] rom_raddr" in rtl
    assert "rom_waddr" not in rtl
    assert "rom_wren" not in rtl


def test_write_systemverilog_external_write_only_range_ports() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="WBUF",
                address=0x40,
                address_end=0x4F,
                hw_access="external",
                fields=[Field("BUFFER", 31, 0, "wo", 0)],
            )
        ]
    )
    rtl = write_systemverilog(model, "axi4-lite", section_heading="External Wbuf")
    assert "output logic [1:0] wbuf_waddr" in rtl
    assert "wbuf_raddr" not in rtl
    assert "wbuf_rden" not in rtl


def test_write_systemverilog_skips_interface_comment_for_none_only_register() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="RSVD_BLOCK",
                address=0x8,
                fields=[Field("RSVD", 31, 0, "none", 0)],
            )
        ]
    )
    rtl = write_systemverilog(model, "axi4-lite", section_heading="Reserved")
    port_block = rtl.split("// Register interfaces", 1)[1].split(");", 1)[0]
    assert "RSVD_BLOCK" not in port_block


def test_write_systemverilog_external_write_only_register() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="CMD",
                address=0,
                hw_access="external",
                fields=[Field("OP", 7, 0, "wo", 0)],
            )
        ]
    )
    rtl = write_systemverilog(model, "axi4-lite", section_heading="Commands")
    assert "cmd_wren" in rtl
    assert "cmd_rden" not in rtl
    assert "cmd_rdatavalid" not in rtl
    assert "cmd_read_data[7:0] = 8'h0" in rtl


def test_write_systemverilog_external_read_only_register() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="STAT",
                address=0,
                hw_access="external",
                fields=[Field("FLAG", 0, 0, "ro", 0)],
            )
        ]
    )
    rtl = write_systemverilog(model, "axi4-lite", section_heading="Status")
    assert "stat_rden" in rtl
    assert "stat_wren" not in rtl
    assert "stat_wdata" not in rtl


def test_write_systemverilog_internal_access_variants_and_multibyte_strobe() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0,
                fields=[
                    Field("SET", 0, 0, "rw1s", 0),
                    Field("CLR", 1, 1, "rw0c", 0),
                    Field("PULSE", 2, 2, "r0w1c", 0),
                ],
            ),
            Register(
                name="WIDE",
                address=4,
                fields=[Field("VALUE", 17, 0, "rw", 0)],
            ),
        ]
    )
    rtl = write_systemverilog(model, "axi4-lite", section_heading="Control")
    assert "ctrl_q[0:0] <= ctrl_q[0:0] | s_axi_wdata[0:0]" in rtl
    assert "ctrl_q[1:1] <= ctrl_q[1:1] & s_axi_wdata[1:1]" in rtl
    assert "ctrl_q[2:2] <= ctrl_q[2:2] & ~s_axi_wdata[2:2]" in rtl
    assert "(s_axi_wstrb[0] || s_axi_wstrb[1] || s_axi_wstrb[2])" in rtl


def test_write_systemverilog_file_writes_output(tmp_path: Path) -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    output = tmp_path / "csr.sv"
    write_systemverilog_file(
        output, model, "axi4-lite", section_heading=_golden_section()
    )
    assert output.read_text(encoding="utf-8") == write_systemverilog(
        model, "axi4-lite", section_heading=_golden_section()
    )


def test_write_systemverilog_internal_axi_only_always_ff() -> None:
    """Register with AXI writes but no hw rdata feedback uses the axi-only branch."""
    model = RegisterModel(
        registers=[
            Register(
                name="CMD",
                address=0,
                fields=[Field("OP", 7, 0, "wo", 0)],
            )
        ]
    )
    rtl = write_systemverilog(model, "axi4-lite", section_heading="Commands")
    assert "if (write_en && hit_cmd) begin" in rtl
    assert "cmd_q[7:0] <= s_axi_wdata[7:0]" in rtl
    assert "cmd_op_d" not in rtl
    assert "cmd_q[0:0] <= cmd_op_d" not in rtl


def test_register_read_always_comb_internal_deferred_read() -> None:
    register = Register(
        name="STAT",
        address=0,
        fields=[Field("FLAG", 0, 0, "rw", 0)],
    )
    lines = _register_read_always_comb(register, immediate_read=False)
    text = "\n".join(lines)
    assert "if (read_resp_ready) begin" in text
    assert "stat_read_ok = 1'b1;" in text
    assert "stat_read_data[0:0] = stat_q[0:0];" in text
    assert text.count("end") >= 2


def test_external_read_helper_empty_register_list() -> None:
    assert _external_read_needs_wait_expr([]) == "1'b0"
    assert _external_rdatavalid_hit_terms([]) == "1'b0"


def test_response_logic_empty_register_list() -> None:
    lines = _response_logic(RegisterModel(registers=[]))
    assert "assign write_ok = 1'b0;" in "\n".join(lines)


def test_field_axi_write_update_returns_none_for_non_writable() -> None:
    assert _field_axi_write_update(Field("RO", 0, 0, "ro", 0), "ctrl_q") is None


def test_field_axi_write_update_returns_none_for_unrecognized_access() -> None:
    field = Field("X", 0, 0, "rw", 0)
    object.__setattr__(field, "access", "custom")
    assert _field_axi_write_update(field, "ctrl_q") is None


def test_field_read_expr_reads_storage_when_no_field_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register = Register(name="MEM", address=0, fields=[Field("VAL", 3, 0, "rw", 0)])
    field = register.fields[0]

    monkeypatch.setattr(
        "csr_gen.output.systemverilog_writer._field_has_d_port",
        lambda _field: False,
    )

    assert _field_read_expr(register, field, use_storage=True) == "mem_q[3:0]"
    assert _field_read_expr(register, field, use_storage=False) == "4'h0"


def test_field_read_expr_none_access_returns_reset_literal() -> None:
    register = Register(
        name="RSVD",
        address=0,
        fields=[Field("RSVD", 7, 0, "none", 0xA5)],
    )
    field = register.fields[0]
    assert _field_read_expr(register, field, use_storage=False) == "8'hA5"


def test_field_read_expr_returns_d_port_for_readable_field() -> None:
    register = Register(
        name="STAT",
        address=0,
        fields=[Field("FLAG", 0, 0, "ro", 0)],
    )
    field = register.fields[0]
    assert _field_read_expr(register, field, use_storage=False) == "stat_flag_d"
