"""Tests for BitfieldFieldInspector (requires PySide6)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from csr_gen.model import Field
from csr_gen_gui.widgets.bitfield_inspector import BitfieldFieldInspector


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


def test_inspector_disabled_when_no_selection(qapp) -> None:
    inspector = BitfieldFieldInspector()
    inspector.set_field(None)
    assert inspector._access.isEnabled() is False
    assert inspector._reset.isEnabled() is False


def test_inspector_emits_access_changed(qapp) -> None:
    field = Field(name="CTRL", msb=3, lsb=0, access="rw", reset=0)
    inspector = BitfieldFieldInspector()
    inspector.set_field(field)
    seen: list[str] = []
    inspector.access_changed.connect(seen.append)
    inspector._access.setCurrentText("ro")
    assert seen == ["ro"]


def test_inspector_emits_reset_changed(qapp) -> None:
    field = Field(name="CTRL", msb=3, lsb=0, access="rw", reset=0)
    inspector = BitfieldFieldInspector()
    inspector.set_field(field)
    seen: list[int] = []
    inspector.reset_changed.connect(seen.append)
    inspector._reset.setText("0x5")
    inspector._reset.editingFinished.emit()
    assert seen == [5]
