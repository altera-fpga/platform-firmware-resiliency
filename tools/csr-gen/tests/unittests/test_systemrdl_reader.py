import pytest

from csr_gen.errors import CsrValidationError
from csr_gen.input.systemrdl_reader import (
    SystemRdlParseError,
    list_systemrdl_addrmap_instances,
    list_systemrdl_addrmap_instances_file,
    load_systemrdl,
    load_systemrdl_file,
)
from csr_gen.input.yaml_reader import load_yaml_file
from csr_gen.output.systemrdl_writer import write_systemrdl
from model_compare import assert_models_equal
from test_paths import REPO_ROOT, TESTDATA

GOLDEN_ROOT = REPO_ROOT / "specs" / "golden"
SYSTMRDL_TESTDATA = TESTDATA / "systemrdl"


def test_load_golden_example_device() -> None:
    case_dir = GOLDEN_ROOT / "example-device"
    model = load_yaml_file(case_dir / "model.yml")
    spec = load_systemrdl_file(case_dir / "expected.rdl")
    assert spec.section_heading == "CSR Registers"
    assert spec.addrmap_name == "csr_registers"
    assert_models_equal(model, spec.model)


def test_load_golden_external_device() -> None:
    case_dir = GOLDEN_ROOT / "external-device"
    model = load_yaml_file(case_dir / "model.yml")
    spec = load_systemrdl_file(case_dir / "expected.rdl")
    assert_models_equal(model, spec.model)


def test_load_systemrdl_import_to_markdown_round_trip() -> None:
    case_dir = GOLDEN_ROOT / "example-device"
    original = load_systemrdl_file(case_dir / "expected.rdl")
    from csr_gen.output.markdown_writer import write_markdown

    markdown = write_markdown(
        original.model,
        original.section_heading,
        section_heading=original.section_heading,
    )
    from csr_gen.input.markdown_reader import load_markdown

    restored = load_markdown(markdown, original.section_heading)
    assert_models_equal(original.model, restored.model)


def test_load_systemrdl_rejects_multiple_top_level_addrmaps() -> None:
    rdl = """
property csr_gen_access { type = string; component = field; };
addrmap one {} addrmap two {};
"""
    with pytest.raises(SystemRdlParseError):
        load_systemrdl(rdl, "multi.rdl")


def test_load_systemrdl_rejects_register_without_fields() -> None:
    rdl = """
property csr_gen_access { type = string; component = field; };
addrmap top {
    reg { regwidth = 32; } EMPTY @ 0x0;
};
"""
    with pytest.raises(SystemRdlParseError):
        load_systemrdl(rdl, "empty.rdl")


def test_load_systemrdl_imports_regfile_registers() -> None:
    path = SYSTMRDL_TESTDATA / "hierarchical_regfile.rdl"
    spec = load_systemrdl_file(path)
    assert spec.section_heading == "Hierarchical Regfile Device"
    assert len(spec.model.registers) == 3

    direct = spec.model.registers[0]
    assert direct.name == "DIRECT"
    assert direct.address == 0x0

    inner = spec.model.registers[1]
    assert inner.name == "INNER"
    assert inner.address == 0x100

    stat = spec.model.registers[2]
    assert stat.name == "STAT"
    assert stat.address == 0x104


def test_load_systemrdl_imports_nested_addrmap_registers() -> None:
    path = SYSTMRDL_TESTDATA / "hierarchical_nested_addrmap.rdl"
    spec = load_systemrdl_file(path)
    assert spec.section_heading == "Nested Addrmap Device"
    assert len(spec.model.registers) == 2

    top = spec.model.registers[0]
    assert top.name == "TOP"
    assert top.address == 0x0

    child = spec.model.registers[1]
    assert child.name == "CHILD"
    assert child.address == 0x1010


def test_load_systemrdl_requires_addrmap_selector_for_multi_peripheral() -> None:
    path = SYSTMRDL_TESTDATA / "hierarchical_multi_peripheral.rdl"
    with pytest.raises(SystemRdlParseError, match="multiple nested addrmap"):
        load_systemrdl_file(path)


def test_load_systemrdl_imports_selected_nested_addrmap() -> None:
    path = SYSTMRDL_TESTDATA / "hierarchical_multi_peripheral.rdl"
    spec = load_systemrdl_file(path, addrmap_instance="uart_inst")
    assert spec.section_heading == "UART"
    assert spec.addrmap_name == "uart_inst"
    assert len(spec.model.registers) == 1
    assert spec.model.registers[0].name == "UART_TX"
    assert spec.model.registers[0].address == 0x0


def test_load_systemrdl_rejects_unknown_addrmap_instance() -> None:
    path = SYSTMRDL_TESTDATA / "hierarchical_multi_peripheral.rdl"
    with pytest.raises(SystemRdlParseError, match="no nested addrmap instance"):
        load_systemrdl_file(path, addrmap_instance="missing_inst")


def test_load_systemrdl_rejects_addrmap_instance_on_flat_file() -> None:
    path = SYSTMRDL_TESTDATA / "native_flat.rdl"
    with pytest.raises(SystemRdlParseError, match="no nested addrmap instance"):
        load_systemrdl_file(path, addrmap_instance="missing_inst")


def test_load_systemrdl_selects_top_by_addrmap_instance_name() -> None:
    path = SYSTMRDL_TESTDATA / "hierarchical_nested_addrmap.rdl"
    spec = load_systemrdl_file(path, addrmap_instance="nested_device")
    assert spec.addrmap_name == "nested_device"
    assert len(spec.model.registers) == 2
    assert {register.name for register in spec.model.registers} == {"TOP", "CHILD"}


def test_load_systemrdl_selects_single_nested_addrmap_by_instance_name() -> None:
    path = SYSTMRDL_TESTDATA / "hierarchical_nested_addrmap.rdl"
    spec = load_systemrdl_file(path, addrmap_instance="child_inst")
    assert spec.section_heading == "Child Block"
    assert len(spec.model.registers) == 1
    assert spec.model.registers[0].name == "CHILD"
    assert spec.model.registers[0].address == 0x1010


def test_load_systemrdl_prefixes_regfile_register_names_on_collision() -> None:
    rdl = """
property csr_gen_access { type = string; component = field; };
addrmap top {
    reg {
        regwidth = 32;
        field { sw = rw; csr_gen_access = "rw"; } a[0:0] = 0;
    } STATUS @ 0x0;
    regfile bank_a {
        reg {
            regwidth = 32;
            field { sw = rw; csr_gen_access = "rw"; } a[0:0] = 0;
        } STATUS @ 0x0;
    } bank_a_inst @ 0x100;
    regfile bank_b {
        reg {
            regwidth = 32;
            field { sw = rw; csr_gen_access = "rw"; } a[0:0] = 0;
        } STATUS @ 0x0;
    } bank_b_inst @ 0x200;
};
"""
    spec = load_systemrdl(rdl, "collision.rdl")
    names = [register.name for register in spec.model.registers]
    assert names == ["STATUS", "BANK_A_INST_STATUS", "BANK_B_INST_STATUS"]
    assert [register.address for register in spec.model.registers] == [
        0x0,
        0x100,
        0x200,
    ]


def test_load_systemrdl_rejects_invalid_address_end() -> None:
    rdl = """
property csr_gen_access { type = string; component = field; };
property csr_gen_address_end { type = longint; component = reg; };
addrmap top {
    reg {
        regwidth = 32;
        csr_gen_address_end = 0x1;
        field { sw = rw; csr_gen_access = "rw"; } a[0:0] = 0;
    } BAD @ 0x10;
};
"""
    with pytest.raises(SystemRdlParseError, match="before its base address"):
        load_systemrdl(rdl, "bad-end.rdl")


def test_load_systemrdl_rejects_unaligned_address_end() -> None:
    rdl = """
property csr_gen_access { type = string; component = field; };
property csr_gen_address_end { type = longint; component = reg; };
addrmap top {
    reg {
        regwidth = 32;
        csr_gen_address_end = 0x11;
        field { sw = rw; csr_gen_access = "rw"; } a[0:0] = 0;
    } BAD @ 0x10;
};
"""
    with pytest.raises(SystemRdlParseError, match="4-byte aligned"):
        load_systemrdl(rdl, "bad-range.rdl")


def test_load_systemrdl_imports_leon2_uart_with_unset_field_reset() -> None:
    path = TESTDATA / "systemrdl" / "SystemRDL_1.0" / "Examples" / "Leon2" / "uart.rdl"
    spec = load_systemrdl_file(path)
    assert len(spec.model.registers) >= 4
    data_fields = [
        field
        for register in spec.model.registers
        for field in register.fields
        if field.name == "DATA"
    ]
    assert data_fields
    assert data_fields[0].reset == 0


def test_load_systemrdl_imports_native_third_party_rdl() -> None:
    path = SYSTMRDL_TESTDATA / "native_flat.rdl"
    spec = load_systemrdl_file(path)
    assert spec.section_heading == "Native Flat Device"
    assert len(spec.model.registers) == 3

    ctrl = spec.model.registers[0]
    assert ctrl.name == "CTRL"
    assert ctrl.fields[0].access == "rw"
    assert ctrl.fields[1].access == "rc"

    fifo = spec.model.registers[1]
    assert fifo.hw_access == "external"
    assert fifo.address == 0x10

    mem = spec.model.registers[2]
    assert mem.hw_access == "external"
    assert mem.address == 0x20
    assert mem.address_end == 0x2F


def test_load_systemrdl_imports_legacy_address_end_udp() -> None:
    rdl = """
property csr_gen_access { type = string; component = field; };
property csr_gen_address_end { type = longint; component = reg; };
addrmap top {
    external reg {
        regwidth = 32;
        csr_gen_address_end = 0x2c;
        field { sw = rw; hw = rw; csr_gen_access = "rw"; } window[31:0] = 0;
    } MEM @ 0x20;
};
"""
    spec = load_systemrdl(rdl, "legacy-udp.rdl")
    mem = spec.model.registers[0]
    assert mem.address == 0x20
    assert mem.address_end == 0x2F


def test_load_systemrdl_rejects_non_32bit_registers() -> None:
    rdl = """
addrmap top {
    default regwidth = 8;
    reg {
        field { sw = rw; hw = r; } data[7:0] = 0;
    } DATA @ 0x0;
};
"""
    with pytest.raises(SystemRdlParseError, match="regwidth=32"):
        load_systemrdl(rdl, "8bit.rdl")


def test_load_systemrdl_rejects_unsupported_signal_component() -> None:
    rdl = """
addrmap top {
    signal {} clk;
    reg { regwidth = 32; field { sw = rw; hw = rw; } a[0:0] = 0; } CTRL @ 0x0;
};
"""
    with pytest.raises(SystemRdlParseError, match="signal component"):
        load_systemrdl(rdl, "signal.rdl")


def test_load_systemrdl_rejects_unsupported_mem_component() -> None:
    rdl = """
addrmap top {
    external mem { memwidth = 32; mementries = 4; } RAM @ 0x0;
};
"""
    with pytest.raises(SystemRdlParseError, match="memory component"):
        load_systemrdl(rdl, "mem.rdl")


def test_load_systemrdl_rejects_unsupported_access_without_udp() -> None:
    rdl = """
property csr_gen_access { type = string; component = field; };
addrmap top {
    reg {
        regwidth = 32;
        field { sw = na; hw = na; } a[0:0] = 0;
    } BAD @ 0x0;
};
"""
    with pytest.raises(SystemRdlParseError):
        load_systemrdl(rdl, "bad-access.rdl")


def test_load_systemrdl_uses_addrmap_name_when_desc_missing() -> None:
    rdl = """
property csr_gen_access { type = string; component = field; };
addrmap fallback_name {
    reg {
        regwidth = 32;
        field { sw = rw; csr_gen_access = "rw"; } a[0:0] = 0;
    } CTRL @ 0x0;
};
"""
    spec = load_systemrdl(rdl, "no-desc.rdl")
    assert spec.section_heading == "fallback_name"


def test_load_systemrdl_wraps_compiler_errors() -> None:
    with pytest.raises(SystemRdlParseError, match="broken.rdl"):
        load_systemrdl("this is not rdl", "broken.rdl")


def test_load_systemrdl_requires_compiler(monkeypatch) -> None:
    import csr_gen.input.systemrdl_reader as reader

    monkeypatch.setattr(reader, "RDLCompiler", None)
    with pytest.raises(CsrValidationError, match="systemrdl-compiler"):
        load_systemrdl("addrmap top {};", "missing-compiler.rdl")


def test_load_systemrdl_file_reads_from_disk(tmp_path) -> None:
    case_dir = GOLDEN_ROOT / "example-device"
    copied = tmp_path / "copy.rdl"
    copied.write_text(case_dir.joinpath("expected.rdl").read_text(encoding="utf-8"))
    spec = load_systemrdl_file(copied)
    assert spec.section_heading == "CSR Registers"


def test_generated_rdl_matches_writer_for_minimal_model() -> None:
    model = load_yaml_file(GOLDEN_ROOT / "example-device" / "model.yml")
    section = "CSR Registers"
    text = write_systemrdl(model, section_heading=section)
    spec = load_systemrdl(text, "memory.rdl")
    assert_models_equal(model, spec.model)


def test_list_systemrdl_addrmap_instances_for_multi_peripheral() -> None:
    path = SYSTMRDL_TESTDATA / "hierarchical_multi_peripheral.rdl"
    assert list_systemrdl_addrmap_instances_file(path) == ["uart_inst", "spi_inst"]


def test_list_systemrdl_addrmap_instances_returns_empty_for_flat_file() -> None:
    path = SYSTMRDL_TESTDATA / "native_flat.rdl"
    assert list_systemrdl_addrmap_instances_file(path) == []


def test_list_systemrdl_addrmap_instances_wraps_compiler_errors() -> None:
    with pytest.raises(SystemRdlParseError, match="broken.rdl"):
        list_systemrdl_addrmap_instances("this is not rdl", "broken.rdl")


def test_list_systemrdl_addrmap_instances_requires_compiler(monkeypatch) -> None:
    import csr_gen.input.systemrdl_reader as reader

    monkeypatch.setattr(reader, "RDLCompiler", None)
    with pytest.raises(CsrValidationError, match="systemrdl-compiler"):
        list_systemrdl_addrmap_instances("addrmap top {};", "missing-compiler.rdl")


def test_list_systemrdl_addrmap_instances_rejects_multiple_top_level_addrmaps(
    monkeypatch,
) -> None:
    import csr_gen.input.systemrdl_reader as reader

    class FakeAddrmapNode:
        pass

    root = object()
    first = FakeAddrmapNode()
    first.parent = root
    second = FakeAddrmapNode()
    second.parent = root

    class FakeCompiler:
        def register_udp(self, *_args, **_kwargs) -> None:
            return None

        def compile_file(self, _path: str):
            return None

        def elaborate(self):
            return type(
                "Root",
                (),
                {"descendants": lambda self: [first, second]},
            )()

    monkeypatch.setattr(reader, "RDLCompiler", FakeCompiler)
    monkeypatch.setattr(reader, "AddrmapNode", FakeAddrmapNode)

    with pytest.raises(SystemRdlParseError, match="exactly one top-level addrmap"):
        list_systemrdl_addrmap_instances("addrmap top {};", "multi.rdl")
