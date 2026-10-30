"""Tests for Simics DML generation."""

from pathlib import Path

import pytest

from csr_gen.input.markdown_reader import load_markdown_file
from csr_gen.input.yaml_reader import load_yaml_file
from csr_gen.model import Field, Register, RegisterModel
from csr_gen.output.dml_writer import (
    DmlGenerationError,
    _sole_field,
    dml_name_from_section,
    write_dml,
    write_dml_file,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_CASE = REPO_ROOT / "specs" / "golden" / "example-device"
EXTERNAL_CASE = REPO_ROOT / "specs" / "golden" / "external-device"


def _golden_section() -> str:
    return (GOLDEN_CASE / "section.txt").read_text(encoding="utf-8").strip()


def test_golden_yaml_export_matches_expected_dml() -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    expected = (GOLDEN_CASE / "expected.dml").read_text(encoding="utf-8")
    assert write_dml(model, section_heading=_golden_section()) == expected


def test_golden_regs_markdown_export_matches_expected_dml() -> None:
    section = _golden_section()
    model = load_markdown_file(GOLDEN_CASE / "regs.md", section).model
    expected = (GOLDEN_CASE / "expected.dml").read_text(encoding="utf-8")
    assert write_dml(model, section_heading=section) == expected


def test_golden_external_device_matches_expected_dml() -> None:
    section = (EXTERNAL_CASE / "section.txt").read_text(encoding="utf-8").strip()
    model = load_markdown_file(EXTERNAL_CASE / "regs.md", section).model
    expected = (EXTERNAL_CASE / "expected.dml").read_text(encoding="utf-8")
    assert write_dml(model, section_heading=section) == expected


def test_dml_name_from_section_heading() -> None:
    assert dml_name_from_section("CSR Registers") == "csr_registers"


def test_write_dml_requires_section_heading() -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    with pytest.raises(DmlGenerationError, match="section heading"):
        write_dml(model, section_heading="   ")


def test_write_dml_file_writes_output(tmp_path: Path) -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    target = tmp_path / "device.dml"
    write_dml_file(target, model, section_heading=_golden_section())
    assert target.read_text(encoding="utf-8") == (
        GOLDEN_CASE / "expected.dml"
    ).read_text(encoding="utf-8")


def test_write_dml_device_and_bank_use_section_name() -> None:
    text = write_dml(
        load_yaml_file(GOLDEN_CASE / "model.yml"),
        section_heading="CSR Registers",
    )
    assert "device csr_registers;" in text
    assert "bank csr_registers {" in text
    assert 'param desc = "CSR Registers";' in text


def test_write_dml_register_and_field_naming() -> None:
    text = write_dml(
        load_yaml_file(GOLDEN_CASE / "model.yml"),
        section_heading=_golden_section(),
    )
    assert "register CTRL size 4 @ 0x0 {" in text
    assert "field ENABLE @ [0] is (read, write)" in text
    assert "field MODE @ [2:1] is (read, write)" in text
    assert "field RSVD @ [31:3] is (reserved)" in text
    assert "field PENDING @ [7:0] is (read, write_1_clears)" in text


def test_write_dml_field_pascal_case_from_snake_name() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="STAT",
                address=0,
                fields=[Field("idle_cnt", 7, 0, "ro", 0, description="Idle count")],
            )
        ]
    )
    text = write_dml(model, section_heading="Status Block")
    assert "field IDLECNT @ [7:0] is (read_only)" in text


def test_write_dml_escapes_quotes_in_ranged_register_description() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="MEM",
                address=0x20,
                address_end=0x2F,
                description='Say "hello"',
                hw_access="external",
                fields=[Field("window", 31, 0, "rw", 0)],
            )
        ]
    )
    text = write_dml(model, section_heading="CSR Registers")
    assert 'is (read, write) "Say \\"hello\\"";' in text


@pytest.mark.parametrize(
    ("access", "templates"),
    [
        ("none", "reserved"),
        ("ro", "read_only"),
        ("rc", "clear_on_read"),
        ("rw", "read, write"),
        ("wo", "write"),
        ("rw1c", "read, write_1_clears"),
        ("rw1s", "read, write_1_only"),
        ("rw0c", "read, write_0_only"),
        ("r0w1c", "read_zero, write_1_clears"),
    ],
)
def test_write_dml_field_access_templates(access: str, templates: str) -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="REG",
                address=0,
                fields=[Field("flag", 0, 0, access, 0)],
            )
        ]
    )
    text = write_dml(model, section_heading="CSR Registers")
    assert f"field FLAG @ [0] is ({templates})" in text


@pytest.mark.parametrize(
    ("access", "templates"),
    [
        ("rw", "read, write"),
        ("ro", "read_only"),
        ("wo", "write_only"),
    ],
)
def test_write_dml_ranged_register_array_templates(access: str, templates: str) -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="BUF",
                address=0x10,
                address_end=0x1B,
                hw_access="external",
                fields=[Field("data", 31, 0, access, 0, description="Buffer slot")],
            )
        ]
    )
    text = write_dml(model, section_heading="CSR Registers")
    assert (
        f'register BUF[i < 3] @ (0x10 + i * 4) is ({templates}) "Buffer slot";' in text
    )


def test_write_dml_wraps_long_field_descriptions() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0,
                fields=[
                    Field(
                        "mode",
                        0,
                        0,
                        "rw",
                        0,
                        description=(
                            "This description is intentionally long enough to "
                            "require wrapping when rendered as DML comments"
                        ),
                    )
                ],
            )
        ]
    )
    text = write_dml(model, section_heading="CSR Registers")
    assert "// rendered as DML comments" in text


def test_write_dml_includes_register_map_comment() -> None:
    text = write_dml(
        load_yaml_file(GOLDEN_CASE / "model.yml"),
        section_heading=_golden_section(),
    )
    assert "// Register map" in text
    assert "// | CTRL     | 0x00    |" in text


def test_write_dml_imports_utility_and_dml_version() -> None:
    text = write_dml(
        load_yaml_file(GOLDEN_CASE / "model.yml"),
        section_heading=_golden_section(),
    )
    assert text.startswith("// Generated by csr-gen")
    assert "dml 1.4;" in text
    assert 'import "utility.dml";' in text


def test_write_dml_skips_blank_comment_paragraphs() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0,
                description="First line\n\nSecond line",
                fields=[Field("en", 0, 0, "rw", 0)],
            )
        ]
    )
    text = write_dml(model, section_heading="CSR Registers")
    assert "// First line" in text
    assert "// Second line" in text


def test_sole_field_raises_when_ranged_register_has_multiple_fields() -> None:
    register = Register(
        name="MEM",
        address=0x20,
        address_end=0x2F,
        hw_access="external",
        fields=[
            Field("low", 15, 0, "rw", 0),
            Field("high", 31, 16, "rw", 0),
        ],
    )
    with pytest.raises(DmlGenerationError, match="exactly one field"):
        _sole_field(register)


def test_sole_field_returns_only_field_for_ranged_register() -> None:
    field = Field("window", 31, 0, "rw", 0)
    register = Register(
        name="MEM",
        address=0x20,
        address_end=0x2F,
        hw_access="external",
        fields=[field],
    )
    assert _sole_field(register) is field


def test_write_dml_escapes_backslashes_in_section_heading() -> None:
    model = RegisterModel(
        registers=[
            Register(name="REG", address=0, fields=[Field("flag", 0, 0, "rw", 0)])
        ]
    )
    text = write_dml(model, section_heading=r"CSR\Registers")
    assert r'param desc = "CSR\\Registers";' in text


def test_write_dml_ranged_register_uses_field_description_when_register_empty() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="BUF",
                address=0x10,
                address_end=0x1B,
                hw_access="external",
                fields=[
                    Field("data", 31, 0, "rw", 0, description="Buffer slot from field")
                ],
            )
        ]
    )
    text = write_dml(model, section_heading="CSR Registers")
    assert 'is (read, write) "Buffer slot from field";' in text


def test_field_dml_name_collapses_hyphenated_tokens() -> None:
    from csr_gen.output.dml_writer import _field_dml_name

    assert _field_dml_name("EN-ABLE") == "ENABLE"


def test_write_dml_field_name_with_hyphen() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0,
                fields=[Field("ENABLE", 0, 0, "rw", 0)],
            )
        ]
    )
    text = write_dml(model, section_heading="CSR Registers")
    assert "field ENABLE @ [0] is (read, write)" in text
