"""Tests for CsrTableWidget (requires PySide6)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from csr_gen.model import Field, Register, RegisterModel
from csr_gen_gui.model_table import model_to_row_dicts
from csr_gen_gui.table_editing import COL_REGISTER, build_row_infos
from csr_gen_gui.widgets.csr_table_widget import CsrTableWidget


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


def _example_rows() -> list[dict[str, str]]:
    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0x00,
                description="Control",
                fields=[
                    Field(name="A", msb=0, lsb=0, access="rw", reset=0),
                    Field(name="B", msb=2, lsb=1, access="rw", reset=0),
                ],
            ),
            Register(
                name="EVENTS",
                address=0x08,
                description="Events",
                fields=[Field(name="P", msb=7, lsb=0, access="rw1c", reset=0)],
            ),
        ]
    )
    return model_to_row_dicts(model)


def test_load_rows_shows_register_expand_indicator(qapp) -> None:
    widget = CsrTableWidget()
    widget.load_rows(_example_rows())

    assert widget.rowCount() == len(build_row_infos(_example_rows()))
    register_item = widget.item(0, COL_REGISTER)
    assert register_item is not None
    assert register_item.text().startswith("[−]")
    assert "CTRL" in register_item.text()


def test_register_collapse_hides_field_rows(qapp) -> None:
    widget = CsrTableWidget()
    widget.load_rows(_example_rows())
    initial_rows = widget.rowCount()

    widget.cellClicked.emit(0, COL_REGISTER)

    assert widget.rowCount() < initial_rows
    register_item = widget.item(0, COL_REGISTER)
    assert register_item is not None
    assert register_item.text().startswith("[+]")


def test_selection_changed_emits_field_index(qapp) -> None:
    widget = CsrTableWidget()
    widget.load_rows(_example_rows())
    seen: list[tuple[int, int]] = []
    widget.selection_changed.connect(
        lambda register_index, field_index: seen.append((register_index, field_index))
    )

    widget.selectRow(2)
    widget.setCurrentCell(2, 0)

    assert seen == [(0, 1)]


def test_select_field_row_expands_collapsed_register(qapp) -> None:
    widget = CsrTableWidget()
    widget.load_rows(_example_rows())
    widget.cellClicked.emit(0, COL_REGISTER)
    assert widget.rowCount() == 3

    assert widget.select_field_row(0, 0) is True
    assert widget.currentRow() == 1
    assert widget.rowCount() == 5


def test_select_register_row_selects_definition_row(qapp) -> None:
    widget = CsrTableWidget()
    widget.load_rows(_example_rows())

    assert widget.select_register_row(1) is True
    assert widget.currentRow() == 3
