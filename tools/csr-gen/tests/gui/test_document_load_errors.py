"""Tests for Markdown document load error reporting."""

from pathlib import Path

import pytest

from csr_gen.errors import MarkdownParseError
from csr_gen.input.markdown_reader import load_markdown
from csr_gen.literals import HexLiteralError, parse_address_text
from csr_gen_gui.document import DocumentController
from csr_gen_gui.markdown_document import DocumentLoadError, load_document_file


def test_duplicate_heading_message_lists_levels() -> None:
    markdown = """# I2C Registers

## I2C Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x0 | ENABLE | 0 | rw | 0x0 | Enable |
"""
    with pytest.raises(
        MarkdownParseError, match=r"found 2: H1 'I2C Registers', H2"
    ) as error:
        load_markdown(markdown, "I2C Registers")
    assert "Rename the document title" in str(error.value)


def test_en_dash_address_range_rejected() -> None:
    with pytest.raises(HexLiteralError, match="ASCII hyphen"):
        parse_address_text("0x8000\u20130x15ffff")


def test_non_csr_subsection_table_error_mentions_documentation_tables() -> None:
    markdown = """## CSR Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x0 | ENABLE | 0 | rw | 0x0 | Enable |

### Notes

| Value | Name | Meaning |
| --- | --- | --- |
| 0 | NONE | No error |
"""
    with pytest.raises(MarkdownParseError, match="Move documentation tables") as error:
        load_markdown(markdown, "CSR Registers")
    assert "missing required column" in str(error.value)


def test_gui_load_surfaces_duplicate_heading_error(tmp_path: Path) -> None:
    path = tmp_path / "dup.md"
    path.write_text(
        """# CSR Registers

## CSR Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x0 | ENABLE | 0 | rw | 0x0 | Enable |
""",
        encoding="utf-8",
    )
    with pytest.raises(DocumentLoadError, match="Failed to load CSR bank") as error:
        load_document_file(path)
    assert "H1 'CSR Registers'" in str(error.value)


def test_gui_load_surfaces_non_csr_subsection_table(tmp_path: Path) -> None:
    path = tmp_path / "notes.md"
    path.write_text(
        """## CSR Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x0 | ENABLE | 0 | rw | 0x0 | Enable |

### ECODE values

| Value | Name | Meaning |
| --- | --- | --- |
| 0 | NONE | Ok |
""",
        encoding="utf-8",
    )
    controller = DocumentController()
    with pytest.raises(DocumentLoadError, match="documentation tables"):
        controller.load(path)


def test_gui_load_skips_prose_only_section(tmp_path: Path) -> None:
    path = tmp_path / "mixed.md"
    path.write_text(
        """## CSR Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x0 | ENABLE | 0 | rw | 0x0 | Enable |

## Programming notes

See the architecture doc for bring-up steps.
""",
        encoding="utf-8",
    )
    document = load_document_file(path)
    assert len(document.banks) == 1
    assert document.banks[0].section_heading == "CSR Registers"
