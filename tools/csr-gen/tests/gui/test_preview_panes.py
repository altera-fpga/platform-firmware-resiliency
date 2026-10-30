"""Tests for GUI preview pane visibility."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from csr_gen_gui.preview_panes import (
    PREVIEW_PANE_SPECS,
    default_preview_pane_visibility,
)


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


def test_default_preview_pane_visibility_shows_all_panes() -> None:
    visibility = default_preview_pane_visibility()
    assert set(visibility) == {spec.pane_id for spec in PREVIEW_PANE_SPECS}
    assert all(visibility.values())


def test_main_window_preview_pane_menu_defaults(qapp) -> None:
    from csr_gen_gui.main_window import MainWindow

    window = MainWindow()
    try:
        window.show()
        qapp.processEvents()
        for spec in PREVIEW_PANE_SPECS:
            action = window._preview_pane_actions[spec.pane_id]
            assert action.isChecked()
            index = window._preview_pane_tab_indexes[spec.pane_id]
            assert window._preview_tabs.isTabVisible(index)
        assert window._preview_panel.isVisible()
        assert window._preview_header.isVisible()
    finally:
        window.close()


def test_main_window_preview_pane_toggle_hides_tab_and_header(qapp) -> None:
    from csr_gen_gui.main_window import MainWindow

    window = MainWindow()
    try:
        window.show()
        qapp.processEvents()
        dml_action = window._preview_pane_actions["dml"]
        dml_index = window._preview_pane_tab_indexes["dml"]

        dml_action.setChecked(False)
        qapp.processEvents()
        assert window._preview_tabs.isTabVisible(dml_index) is False

        dml_action.setChecked(True)
        qapp.processEvents()
        assert window._preview_tabs.isTabVisible(dml_index) is True

        sv_action = window._preview_pane_actions["systemverilog"]
        sv_action.setChecked(False)
        qapp.processEvents()
        assert window._preview_header.isVisible() is False

        sv_action.setChecked(True)
        qapp.processEvents()
        assert window._preview_header.isVisible() is True
    finally:
        window.close()


def test_main_window_hiding_all_preview_panes_hides_panel(qapp) -> None:
    from csr_gen_gui.main_window import MainWindow

    window = MainWindow()
    try:
        window.show()
        qapp.processEvents()
        for action in window._preview_pane_actions.values():
            action.setChecked(False)
        qapp.processEvents()
        assert window._preview_panel.isVisible() is False

        window._preview_pane_actions["c_header"].setChecked(True)
        qapp.processEvents()
        assert window._preview_panel.isVisible() is True
    finally:
        window.close()
