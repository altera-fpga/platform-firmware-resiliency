"""Tests for AddressMapWidget timeline (requires PySide6)."""

from __future__ import annotations

import subprocess
import sys

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from csr_gen.model import Field, Register, RegisterModel


def test_module_import_before_qapplication() -> None:
    """Importing the widget module must not require QGuiApplication."""
    script = """
from PySide6.QtWidgets import QApplication
assert QApplication.instance() is None
import csr_gen_gui.widgets.address_map_widget as address_map_widget
assert address_map_widget.min_register_block_height() == (
    address_map_widget._DEFAULT_MIN_REGISTER_BLOCK_HEIGHT
)
assert address_map_widget.AddressMapWidget.pixels_per_slot() == (
    address_map_widget.min_register_block_height()
)
"""
    subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        text=True,
    )


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


def test_set_selected_register_updates_property(qapp) -> None:
    from csr_gen_gui.widgets.address_map_widget import AddressMapWidget

    model = RegisterModel(
        registers=[
            Register(
                name="A",
                address=0x00,
                fields=[Field(name="X", msb=0, lsb=0, access="rw", reset=0)],
            ),
            Register(
                name="B",
                address=0x08,
                fields=[Field(name="Y", msb=0, lsb=0, access="rw", reset=0)],
            ),
        ]
    )
    widget = AddressMapWidget()
    widget.set_model(model, selected_register_index=1)

    widget.set_selected_register(0)

    assert widget.selected_register_index == 0


def test_register_selected_signal_on_programmatic_update_not_emitted(qapp) -> None:
    from csr_gen_gui.widgets.address_map_widget import AddressMapWidget

    model = RegisterModel(
        registers=[
            Register(
                name="A",
                address=0x00,
                fields=[Field(name="X", msb=0, lsb=0, access="rw", reset=0)],
            ),
        ]
    )
    widget = AddressMapWidget()
    widget.set_model(model)
    seen: list[int] = []
    widget.register_selected.connect(seen.append)

    widget.set_selected_register(0)

    assert seen == []
