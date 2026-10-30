"""Tests for C header generation."""

from pathlib import Path

import pytest

from csr_gen.input.markdown_reader import load_markdown_file
from csr_gen.input.yaml_reader import load_yaml_file
from csr_gen.model import Field, Register, RegisterModel
from csr_gen.output.c_header_writer import (
    CHeaderGenerationError,
    macro_prefix_from_section,
    write_c_header,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_CASE = REPO_ROOT / "specs" / "golden" / "example-device"


def _golden_section() -> str:
    return (GOLDEN_CASE / "section.txt").read_text(encoding="utf-8").strip()


def _assert_comment_table_rows_within_width(
    header: str, *, max_width: int = 80
) -> None:
    for line in header.splitlines():
        if line.startswith(" *  |") or line.startswith(" *  +"):
            assert len(line) <= max_width, line


def test_golden_yaml_export_matches_expected_h() -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    expected = (GOLDEN_CASE / "expected.h").read_text(encoding="utf-8")
    header = write_c_header(model, section_heading=_golden_section())
    assert header == expected
    _assert_comment_table_rows_within_width(header)


def test_golden_regs_markdown_export_matches_expected_h() -> None:
    section = _golden_section()
    model = load_markdown_file(GOLDEN_CASE / "regs.md", section).model
    expected = (GOLDEN_CASE / "expected.h").read_text(encoding="utf-8")
    header = write_c_header(model, section_heading=section)
    assert header == expected
    _assert_comment_table_rows_within_width(header)


def test_macro_prefix_from_section_heading() -> None:
    assert macro_prefix_from_section("CSR Registers") == "CSR_REGISTERS"


def test_write_c_header_requires_section_heading() -> None:
    model = load_yaml_file(GOLDEN_CASE / "model.yml")
    with pytest.raises(CHeaderGenerationError, match="section heading"):
        write_c_header(model, section_heading="   ")


def test_write_c_header_omits_none_access_field_macros() -> None:
    header = write_c_header(
        load_yaml_file(GOLDEN_CASE / "model.yml"),
        section_heading=_golden_section(),
    )
    assert "CSR_REGISTERS_CTRL_RSVD_MASK" not in header
    assert "| RSVD   | 31:3 | none   |" in header


def test_write_c_header_usage_and_field_manipulation() -> None:
    header = write_c_header(
        load_yaml_file(GOLDEN_CASE / "model.yml"),
        section_heading=_golden_section(),
    )
    assert "This header does not" in header
    assert "reg_read(" in header
    assert "reg_write(" in header
    assert "#ifndef CSR_REGISTERS_H" in header
    assert "#ifndef CSR_REGISTERS_BASE_ADDR" in header
    assert "#include <stdint.h>" in header
    assert 'extern "C" {' in header
    assert "CSR_REGISTERS_CTRL_ENABLE_GET(reg)" in header
    assert "CSR_REGISTERS_CTRL_ENABLE_SET(reg, val)" in header
    assert "CSR_REGISTERS_CTRL_ENABLE_MASK))))" in header
    assert "typedef union" not in header
    assert "_t;" not in header


def test_write_c_header_wraps_long_table_descriptions() -> None:
    long_text = "description " * 12
    model = RegisterModel(
        registers=[
            Register(
                name="STAT",
                address=0,
                description=long_text,
                fields=[
                    Field(
                        "COUNT",
                        15,
                        0,
                        "ro",
                        0,
                        description=long_text,
                    )
                ],
            )
        ]
    )
    header = write_c_header(model, section_heading="Stats")
    _assert_comment_table_rows_within_width(header)
    assert long_text[:20] in header
    assert "|" in header
