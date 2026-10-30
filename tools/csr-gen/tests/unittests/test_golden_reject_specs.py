"""Validate negative golden Markdown CSR specifications."""

from pathlib import Path

import pytest

from csr_gen.errors import CsrValidationError
from csr_gen.input.markdown_reader import load_markdown_file

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_REJECT_ROOT = REPO_ROOT / "specs" / "golden-reject"


def _golden_reject_case_dirs() -> list[Path]:
    if not GOLDEN_REJECT_ROOT.is_dir():
        return []
    return sorted(path for path in GOLDEN_REJECT_ROOT.iterdir() if path.is_dir())


@pytest.mark.parametrize(
    "case_dir", _golden_reject_case_dirs(), ids=lambda path: path.name
)
def test_golden_reject_markdown_fails_validation(case_dir: Path) -> None:
    markdown_path = case_dir / "regs.md"
    section_path = case_dir / "section.txt"
    error_path = case_dir / "error.txt"

    assert markdown_path.is_file(), f"{case_dir} must contain regs.md"
    assert section_path.is_file(), f"{case_dir} must contain section.txt"
    assert error_path.is_file(), f"{case_dir} must contain error.txt"

    section = section_path.read_text(encoding="utf-8").strip()
    expected = error_path.read_text(encoding="utf-8").strip()

    with pytest.raises(CsrValidationError) as error:
        load_markdown_file(markdown_path, section)

    combined = "\n".join(error.value.messages)
    assert expected in combined
