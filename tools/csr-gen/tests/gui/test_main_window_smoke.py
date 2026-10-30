"""Smoke test that constructs the Qt main window (requires PySide6)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


def test_main_opens_initial_file(qapp) -> None:
    from csr_gen_gui.main_window import MainWindow

    golden = (
        Path(__file__).resolve().parents[2]
        / "specs"
        / "golden"
        / "example-device"
        / "regs.md"
    )
    window = MainWindow()
    assert window.open_document_path(golden, confirm_discard=False) is True
    assert window.windowTitle().startswith("regs.md")
    window.close()


def test_main_window_constructs(qapp) -> None:
    from csr_gen_gui.main_window import MainWindow

    window = MainWindow()
    assert window.windowTitle() == "Untitled — csr-gen"
    window.close()
