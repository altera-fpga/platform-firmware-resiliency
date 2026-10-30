"""Tests for GUI preview syntax highlighting."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from csr_gen_gui.syntax_highlighting import (
    PreviewLanguage,
    _C_KEYWORDS,
    _DML_KEYWORDS,
    _SV_KEYWORDS,
    _SYSTEMRDL_KEYWORDS,
    _keyword_pattern,
    attach_preview_highlighter,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN = REPO_ROOT / "specs" / "golden" / "example-device"


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


def test_keyword_patterns_match_golden_tokens() -> None:
    sv_text = (GOLDEN / "expected.sv").read_text(encoding="utf-8")
    sv_matches = {
        match.group(0) for match in _keyword_pattern(_SV_KEYWORDS).finditer(sv_text)
    }
    assert "module" in sv_matches
    assert "endmodule" in sv_matches
    assert "input" in sv_matches

    c_text = (GOLDEN / "expected.h").read_text(encoding="utf-8")
    c_matches = {
        match.group(0)
        for match in _keyword_pattern(_C_KEYWORDS | _DML_KEYWORDS).finditer(c_text)
    }
    assert "extern" in c_matches
    assert "define" not in c_matches

    dml_text = (GOLDEN / "expected.dml").read_text(encoding="utf-8")
    dml_matches = {
        match.group(0)
        for match in _keyword_pattern(_C_KEYWORDS | _DML_KEYWORDS).finditer(dml_text)
    }
    assert "device" in dml_matches
    assert "register" in dml_matches
    assert "write_1_clears" in dml_matches

    rdl_text = (GOLDEN / "expected.rdl").read_text(encoding="utf-8")
    rdl_matches = {
        match.group(0)
        for match in _keyword_pattern(_SYSTEMRDL_KEYWORDS).finditer(rdl_text)
    }
    assert "addrmap" in rdl_matches
    assert "field" in rdl_matches
    assert "woclr" in rdl_matches


def test_xml_patterns_match_golden_ipxact() -> None:
    xml_text = (GOLDEN / "expected.xml").read_text(encoding="utf-8")
    tag_pattern = re.compile(r"</?(?:\w+:)?[\w-]+")
    tags = {match.group(0) for match in tag_pattern.finditer(xml_text)}
    assert "<ipxact:register" in tags
    assert "<ipxact:field" in tags

    assert re.search(r"'h[0-9a-fA-F]+", xml_text) is not None
    assert re.search(r"<\?xml.*\?>", xml_text) is not None


def test_clike_preprocessor_pattern_matches_guard() -> None:
    c_text = (GOLDEN / "expected.h").read_text(encoding="utf-8")
    pattern = re.compile(
        r"#\s*(?:define|include|ifndef|ifdef|endif|else|elif|undef|pragma)\b[^\n]*"
    )
    matches = [match.group(0) for match in pattern.finditer(c_text)]
    assert any("#ifndef" in line for line in matches)
    assert any("#define" in line for line in matches)


@pytest.mark.parametrize(
    ("language", "expected_type"),
    [
        (PreviewLanguage.SYSTEMVERILOG, "SystemVerilogHighlighter"),
        (PreviewLanguage.C_LIKE, "CLikeHighlighter"),
        (PreviewLanguage.SYSTEMRDL, "SystemRdlHighlighter"),
        (PreviewLanguage.XML, "XmlHighlighter"),
        (PreviewLanguage.PLAIN, None),
    ],
)
def test_attach_preview_highlighter(qapp, language, expected_type) -> None:
    from PySide6.QtGui import QTextDocument

    document = QTextDocument()
    highlighter = attach_preview_highlighter(document, language)
    if expected_type is None:
        assert highlighter is None
        return
    assert highlighter.__class__.__name__ == expected_type
    assert highlighter.document() is document
