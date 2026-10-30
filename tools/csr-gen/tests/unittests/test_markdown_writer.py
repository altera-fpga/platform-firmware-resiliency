from pathlib import Path

from csr_gen.input.markdown_reader import load_markdown, load_markdown_file
from csr_gen.output.markdown_writer import write_markdown
from model_compare import assert_models_equal

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_CASE = REPO_ROOT / "specs" / "golden" / "example-device"


def test_write_markdown_uses_fixed_column_order() -> None:
    spec = load_markdown_file(GOLDEN_CASE / "regs.md", "CSR Registers")
    markdown = write_markdown(
        spec.model,
        "CSR Registers",
        section_heading=spec.section_heading,
        heading_level=spec.heading_level,
    )

    header = markdown.splitlines()[2]
    assert header == (
        "| Register | Address | Field | Bits | Access | Reset | HW Access | Description |"
    )


def test_markdown_round_trip_preserves_model(tmp_path: Path) -> None:
    section = (GOLDEN_CASE / "section.txt").read_text(encoding="utf-8").strip()
    original = load_markdown_file(GOLDEN_CASE / "regs.md", section)
    round_trip_path = tmp_path / "roundtrip.md"
    round_trip_path.write_text(
        write_markdown(
            original.model,
            section,
            section_heading=original.section_heading,
            heading_level=original.heading_level,
        ),
        encoding="utf-8",
    )
    restored = load_markdown(round_trip_path.read_text(encoding="utf-8"), section)

    assert_models_equal(original.model, restored.model)


def test_markdown_round_trip_normalizes_names_and_formatting() -> None:
    source = """\
# Registers

| register | field | bits | access | reset | address | description |
| --- | --- | --- | --- | --- | --- | --- |
| ctrl | enable | 0 | rw | 0 | 0x00 | Control |
|  | mode | 2:1 | rw | 0x1 |  | Mode |
"""
    spec = load_markdown(source, "Registers")
    restored = load_markdown(
        write_markdown(
            spec.model,
            "Registers",
            section_heading=spec.section_heading,
            heading_level=spec.heading_level,
        ),
        "Registers",
    )

    assert restored.model.registers[0].name == "CTRL"
    assert restored.model.registers[0].fields[1].reset == 1
    assert restored.model.registers[0].fields[1].name == "MODE"


def test_write_markdown_preserves_source_section_heading_with_mixed_case_query() -> (
    None
):
    spec = load_markdown_file(GOLDEN_CASE / "regs.md", "cSR Registers")
    markdown = write_markdown(
        spec.model,
        "cSR Registers",
        section_heading=spec.section_heading,
        heading_level=spec.heading_level,
    )

    assert markdown.splitlines()[0] == "## CSR Registers"
