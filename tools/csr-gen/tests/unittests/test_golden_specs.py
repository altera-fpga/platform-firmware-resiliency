"""Validate repository golden Markdown CSR specifications."""

from pathlib import Path

import pytest

from csr_gen.input.markdown_reader import load_markdown, load_markdown_file
from csr_gen.input.yaml_reader import load_yaml_file
from csr_gen.output.markdown_writer import write_markdown
from model_compare import assert_models_equal

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_ROOT = REPO_ROOT / "specs" / "golden"


def _golden_case_dirs() -> list[Path]:
    if not GOLDEN_ROOT.is_dir():
        return []
    return sorted(
        path
        for path in GOLDEN_ROOT.iterdir()
        if path.is_dir() and (path / "regs.md").is_file()
    )


def _read_section(section_path: Path) -> str:
    return section_path.read_text(encoding="utf-8").strip()


@pytest.mark.parametrize("case_dir", _golden_case_dirs(), ids=lambda path: path.name)
def test_golden_markdown_matches_model(case_dir: Path) -> None:
    """regs.md and model.yml describe the same register model (parser + validation)."""
    markdown_path = case_dir / "regs.md"
    model_path = case_dir / "model.yml"
    section_path = case_dir / "section.txt"

    assert markdown_path.is_file(), f"{case_dir} must contain regs.md"
    assert model_path.is_file(), f"{case_dir} must contain model.yml"
    assert section_path.is_file(), f"{case_dir} must contain section.txt"

    section = _read_section(section_path)
    markdown_spec = load_markdown_file(markdown_path, section)
    yaml_model = load_yaml_file(model_path)
    assert_models_equal(markdown_spec.model, yaml_model)


@pytest.mark.parametrize("case_dir", _golden_case_dirs(), ids=lambda path: path.name)
def test_golden_yaml_export_matches_expected(case_dir: Path) -> None:
    """model.yml -> Markdown export matches expected.md (generator only)."""
    model_path = case_dir / "model.yml"
    expected_path = case_dir / "expected.md"
    section_path = case_dir / "section.txt"

    assert model_path.is_file(), f"{case_dir} must contain model.yml"
    assert expected_path.is_file(), f"{case_dir} must contain expected.md"
    assert section_path.is_file(), f"{case_dir} must contain section.txt"

    section = _read_section(section_path)
    model = load_yaml_file(model_path)
    expected = expected_path.read_text(encoding="utf-8")
    assert write_markdown(model, section) == expected


@pytest.mark.parametrize("case_dir", _golden_case_dirs(), ids=lambda path: path.name)
def test_golden_expected_markdown_round_trip(case_dir: Path) -> None:
    """expected.md -> model -> Markdown is idempotent (canonical parser + writer)."""
    expected_path = case_dir / "expected.md"
    section_path = case_dir / "section.txt"

    assert expected_path.is_file(), f"{case_dir} must contain expected.md"
    assert section_path.is_file(), f"{case_dir} must contain section.txt"

    section = _read_section(section_path)
    expected = expected_path.read_text(encoding="utf-8")
    spec = load_markdown(expected, section)
    assert (
        write_markdown(
            spec.model,
            section,
            section_heading=spec.section_heading,
            heading_level=spec.heading_level,
        )
        == expected
    )


@pytest.mark.parametrize("case_dir", _golden_case_dirs(), ids=lambda path: path.name)
def test_golden_regs_markdown_export_matches_expected(case_dir: Path) -> None:
    """regs.md -> model -> Markdown matches expected.md (integrated import + export)."""
    markdown_path = case_dir / "regs.md"
    expected_path = case_dir / "expected.md"
    section_path = case_dir / "section.txt"

    assert markdown_path.is_file(), f"{case_dir} must contain regs.md"
    assert expected_path.is_file(), f"{case_dir} must contain expected.md"
    assert section_path.is_file(), f"{case_dir} must contain section.txt"

    section = _read_section(section_path)
    spec = load_markdown_file(markdown_path, section)
    expected = expected_path.read_text(encoding="utf-8")
    assert (
        write_markdown(
            spec.model,
            section,
            section_heading=spec.section_heading,
            heading_level=spec.heading_level,
        )
        == expected
    )
