"""Tests for commercial EDA missing-tool messages."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.end2end.commercial_eda import _arc


def test_require_tool_passes_when_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_arc.shutil, "which", lambda name: "/bin/vcs")
    _arc.require_tool("vcs")


def test_require_tool_reports_missing_tool_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_arc.shutil, "which", lambda name: None)
    monkeypatch.setattr(_arc, "_HINT_FILE", Path("/no/such/eda-tool-hint.txt"))
    with pytest.raises(AssertionError, match="not found on PATH") as exc_info:
        _arc.require_tool("quartus_syn")
    assert str(exc_info.value) == (
        "quartus_syn not found on PATH. Install the tool and put it on PATH."
    )


def test_require_tool_appends_optional_hint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    hint = tmp_path / "eda-tool-hint.txt"
    hint.write_text("see local tool notes\n", encoding="utf-8")
    monkeypatch.setattr(_arc.shutil, "which", lambda name: None)
    monkeypatch.setattr(_arc, "_HINT_FILE", hint)
    with pytest.raises(AssertionError, match="see local tool notes"):
        _arc.require_tool("vcs")
