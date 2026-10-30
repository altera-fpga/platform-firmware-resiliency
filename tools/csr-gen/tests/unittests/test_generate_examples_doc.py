"""Tests for docs/EXAMPLES.md generation."""

from pathlib import Path

from scripts.generate_examples_doc import build_document

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_PATH = REPO_ROOT / "docs" / "EXAMPLES.md"


def test_build_document_includes_golden_cases() -> None:
    document = build_document()
    assert "example-device" in document
    assert "external-device" in document
    assert "## Generated outputs" in document
    assert document.count("#### Rendered") == 2
    assert "Simics DML" in document
    assert "expected.dml" in document
    assert "Markdown is the source of truth" in document
    assert "make doc-examples" not in document


def test_examples_doc_matches_generator_output() -> None:
    assert EXAMPLES_PATH.is_file(), "Run make doc-examples to create docs/EXAMPLES.md"
    assert EXAMPLES_PATH.read_text(encoding="utf-8") == build_document()
