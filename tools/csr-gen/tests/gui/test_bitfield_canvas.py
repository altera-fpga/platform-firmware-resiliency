"""Tests for BitfieldCanvas selection (requires PySide6)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from csr_gen.model import Field, Register
from csr_gen_gui.widgets.bitfield_canvas import BitfieldCanvas


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


def test_set_selected_field_updates_active_index(qapp) -> None:
    register = Register(
        name="CTRL",
        address=0x00,
        fields=[
            Field(name="A", msb=0, lsb=0, access="rw", reset=0),
            Field(name="B", msb=2, lsb=1, access="rw", reset=0),
        ],
    )
    canvas = BitfieldCanvas()
    canvas.set_register(register)

    canvas.set_selected_field(1)

    assert canvas.selected_field_index == 1


def test_paint_register_draws_without_error(qapp) -> None:
    register = Register(
        name="CTRL",
        address=0x00,
        fields=[
            Field(name="A", msb=3, lsb=0, access="rw", reset=0),
            Field(name="B", msb=15, lsb=8, access="rw", reset=0),
        ],
    )
    canvas = BitfieldCanvas()
    canvas.resize(QSize(400, 140))
    canvas.set_register(register)

    pixmap = QPixmap(canvas.size())
    canvas.render(pixmap)

    assert not pixmap.isNull()


def test_field_selected_signal_on_programmatic_update_not_emitted(qapp) -> None:
    register = Register(
        name="CTRL",
        address=0x00,
        fields=[Field(name="A", msb=0, lsb=0, access="rw", reset=0)],
    )
    canvas = BitfieldCanvas()
    canvas.set_register(register)
    seen: list[object] = []
    canvas.field_selected.connect(seen.append)

    canvas.set_selected_field(0)

    assert seen == []


def _point_in_bit(canvas: BitfieldCanvas, bit: int) -> tuple[int, int]:
    lane = canvas._lane_rect()
    x = canvas._bit_x(bit, lane) + 2
    y = lane.center().y()
    return x, y


def test_create_field_in_gap_emits_fields_changed(qapp) -> None:
    register = Register(
        name="CTRL",
        address=0x00,
        fields=[
            Field(name="LOW", msb=3, lsb=0, access="rw", reset=0),
            Field(name="HIGH", msb=31, lsb=16, access="rw", reset=0),
        ],
    )
    canvas = BitfieldCanvas()
    canvas.resize(400, 120)
    canvas.set_register(register)
    changed: list[list[Field]] = []
    canvas.fields_changed.connect(changed.append)

    start_x, start_y = _point_in_bit(canvas, 8)
    end_x, end_y = _point_in_bit(canvas, 10)
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(start_x, start_y),
        QPoint(start_x, start_y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)

    move = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(end_x, end_y),
        QPoint(end_x, end_y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(move)

    release = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(end_x, end_y),
        QPoint(end_x, end_y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseReleaseEvent(release)

    assert len(changed) == 1
    assert len(changed[0]) == 3
    assert changed[0][-1].name == "FIELD"
    assert changed[0][-1].msb == 10
    assert changed[0][-1].lsb == 8


def test_delete_button_removes_field(qapp) -> None:
    register = Register(
        name="CTRL",
        address=0x00,
        fields=[
            Field(name="A", msb=3, lsb=0, access="rw", reset=0),
            Field(name="B", msb=7, lsb=4, access="rw", reset=0),
        ],
    )
    canvas = BitfieldCanvas()
    canvas.resize(400, 120)
    canvas.set_register(register)
    canvas.set_selected_field(0)
    changed: list[list[Field]] = []
    canvas.fields_changed.connect(changed.append)

    lane = canvas._lane_rect()
    rect = canvas._slice_rect(3, 0, lane)
    button = canvas._delete_button_rect(rect)
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(button.center()),
        button.center(),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)

    assert len(changed) == 1
    assert len(changed[0]) == 1
    assert changed[0][0].name == "B"


def test_resize_msb_from_left_edge(qapp) -> None:
    register = Register(
        name="CTRL",
        address=0x00,
        fields=[Field(name="MID", msb=15, lsb=8, access="rw", reset=0)],
    )
    canvas = BitfieldCanvas()
    canvas.resize(800, 120)
    canvas.set_register(register)
    changed: list[list[Field]] = []
    canvas.fields_changed.connect(changed.append)

    lane = canvas._lane_rect()
    rect = canvas._slice_rect(15, 8, lane)
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    start_x = rect.left() + 2
    start_y = rect.center().y()
    target_x = canvas._bit_x(20, lane) + 2

    canvas.mousePressEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(start_x, start_y),
            QPoint(start_x, start_y),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    assert canvas._drag_mode == "resize_msb"

    canvas.mouseMoveEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(target_x, start_y),
            QPoint(target_x, start_y),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    canvas.mouseReleaseEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(target_x, start_y),
            QPoint(target_x, start_y),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )

    assert len(changed) == 1
    assert changed[0][0].msb == 20
    assert changed[0][0].lsb == 8


def test_create_first_field_in_empty_register(qapp) -> None:
    register = Register(name="CTRL", address=0x00, fields=[])
    canvas = BitfieldCanvas()
    canvas.resize(800, 120)
    canvas.set_register(register)
    changed: list[list[Field]] = []
    canvas.fields_changed.connect(changed.append)

    start_x, start_y = _point_in_bit(canvas, 4)
    end_x, _ = _point_in_bit(canvas, 7)
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    canvas.mousePressEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(start_x, start_y),
            QPoint(start_x, start_y),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    canvas.mouseMoveEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(end_x, start_y),
            QPoint(end_x, start_y),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    canvas.mouseReleaseEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(end_x, start_y),
            QPoint(end_x, start_y),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )

    assert len(changed) == 1
    assert len(changed[0]) == 1
    assert changed[0][0].name == "FIELD"
    assert changed[0][0].msb == 7
    assert changed[0][0].lsb == 4


def test_hit_test_reports_resize_and_move_modes(qapp) -> None:
    register = Register(
        name="CTRL",
        address=0x00,
        fields=[Field(name="MID", msb=15, lsb=8, access="rw", reset=0)],
    )
    canvas = BitfieldCanvas()
    canvas.resize(800, 120)
    canvas.set_register(register)
    canvas.set_selected_field(0)
    lane = canvas._lane_rect()
    rect = canvas._slice_rect(15, 8, lane)

    assert (
        canvas._hit_test(rect.topLeft() + QPoint(2, rect.height() // 2)) == "resize_msb"
    )
    assert canvas._hit_test(QPoint(rect.right() - 2, rect.center().y())) == "resize_lsb"
    assert canvas._hit_test(rect.center()) == "move"
