"""Undo/redo integration tests for the Qt main window."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


@pytest.fixture
def main_window(qapp, request):
    from csr_gen_gui.main_window import MainWindow

    window = MainWindow()
    window._confirm_discard = lambda: True
    request.addfinalizer(window.close)
    return window


def test_undo_redo_register_table_edit(main_window) -> None:
    golden = (
        Path(__file__).resolve().parents[2]
        / "specs"
        / "golden"
        / "example-device"
        / "regs.md"
    )
    assert main_window.open_document_path(golden, confirm_discard=False) is True

    rows = main_window._table.all_rows
    original_description = rows[0]["description"]
    edited_rows = [dict(row) for row in rows]
    edited_rows[0]["description"] = "UNDO TEST DESCRIPTION"
    main_window._table.load_rows(edited_rows)
    main_window._on_table_changed()

    assert main_window._undo_stack.canUndo()
    assert main_window._table.all_rows[0]["description"] == "UNDO TEST DESCRIPTION"

    main_window._undo_stack.undo()
    assert main_window._table.all_rows[0]["description"] == original_description
    assert main_window._undo_stack.canRedo()

    main_window._undo_stack.redo()
    assert main_window._table.all_rows[0]["description"] == "UNDO TEST DESCRIPTION"


def test_undo_redo_shortcuts_and_menu_actions(main_window) -> None:
    assert main_window._action_undo.shortcut() == QKeySequence.StandardKey.Undo
    assert QKeySequence("Ctrl+Y") in main_window._action_redo.shortcuts()
    assert QKeySequence("Ctrl+Shift+Z") in main_window._action_redo.shortcuts()
    assert main_window._action_undo.text().startswith("&Undo")
    assert main_window._action_redo.text().startswith("&Redo")


def test_undo_history_clears_on_new_document(main_window) -> None:
    golden = (
        Path(__file__).resolve().parents[2]
        / "specs"
        / "golden"
        / "example-device"
        / "regs.md"
    )
    assert main_window.open_document_path(golden, confirm_discard=False) is True
    rows = main_window._table.all_rows
    edited_rows = [dict(row) for row in rows]
    edited_rows[0]["description"] = "Dirty edit"
    main_window._table.load_rows(edited_rows)
    main_window._on_table_changed()
    assert main_window._undo_stack.canUndo()

    main_window._new_document()
    assert not main_window._undo_stack.canUndo()
    assert not main_window._undo_stack.canRedo()
