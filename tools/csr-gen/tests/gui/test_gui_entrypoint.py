"""Tests for csr-gen-gui startup ordering (requires PySide6)."""

from __future__ import annotations

import subprocess
import sys

import pytest

pytest.importorskip("PySide6")


def test_main_creates_qapplication_before_main_window() -> None:
    """main() must not import MainWindow before constructing QApplication."""
    script = """
from unittest.mock import MagicMock, patch

events = []

class FakeApp:
    def exec(self):
        return 0

def fake_qapplication(argv):
    events.append("qapplication")
    return FakeApp()

import csr_gen_gui.main as gui_main

fake_window = MagicMock()
fake_window.open_document_path.return_value = True

def fake_create_window(*_args, **_kwargs):
    events.append("window")
    return fake_window

with patch("PySide6.QtWidgets.QApplication", fake_qapplication):
    with patch(
        "csr_gen_gui.main_window.create_main_window",
        side_effect=fake_create_window,
    ):
        try:
            gui_main.main([])
        except SystemExit:
            pass

assert events == ["qapplication", "window"]
assert fake_window.open_document_path.called is False
"""
    subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        text=True,
    )


def test_main_opens_file_from_command_line() -> None:
    script = """
from pathlib import Path
from unittest.mock import MagicMock, patch

import csr_gen_gui.main as gui_main

fake_window = MagicMock()
fake_window.open_document_path.return_value = True

with patch("PySide6.QtWidgets.QApplication", return_value=MagicMock(exec=lambda: 0)):
    with patch("csr_gen_gui.main_window.create_main_window", return_value=fake_window):
        try:
            gui_main.main(["example.md"])
        except SystemExit as error:
            assert error.code == 0

fake_window.open_document_path.assert_called_once()
path = fake_window.open_document_path.call_args.args[0]
assert path == Path("example.md").resolve()
assert fake_window.open_document_path.call_args.kwargs["confirm_discard"] is False
"""
    subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        text=True,
    )
