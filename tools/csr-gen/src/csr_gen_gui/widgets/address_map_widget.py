"""Vertical address map timeline widget."""

from __future__ import annotations

from csr_gen.model import RegisterModel
from csr_gen_gui.address_map import (
    AddressGap,
    AddressTimeline,
    TimelineRegister,
    build_address_timeline,
    format_ruler_tick_label,
    register_timeline_label,
    timeline_ruler_ticks,
)

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QMouseEvent,
    QPainter,
    QPaintEvent,
)
from PySide6.QtWidgets import QScrollArea, QSizePolicy, QWidget


def _register_label_font() -> QFont:
    return QFont("Sans Serif", 10)


def _ruler_label_font() -> QFont:
    return QFont("Monospace", 9)


_DEFAULT_MIN_REGISTER_BLOCK_HEIGHT = 46


def min_register_block_height() -> int:
    """Minimum block height for a two-line register label."""
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        return _DEFAULT_MIN_REGISTER_BLOCK_HEIGHT
    metrics = QFontMetrics(_register_label_font())
    return metrics.lineSpacing() * 2 + 10


class AddressMapWidget(QScrollArea):
    """Scrollable vertical address map with 0x0 at the bottom."""

    register_selected = Signal(int)

    _MARGIN = 8
    _RULER_WIDTH = 52
    _LANE_WIDTH = 200
    _TEXT_PADDING = 6
    _PIXELS_PER_SLOT = 44

    @classmethod
    def pixels_per_slot(cls) -> int:
        return max(cls._PIXELS_PER_SLOT, min_register_block_height())

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._canvas = _AddressMapCanvas(self)
        self._canvas.register_selected.connect(self.register_selected.emit)
        self.setWidget(self._canvas)
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(160)

    @property
    def selected_register_index(self) -> int | None:
        return self._canvas.selected_register_index

    def set_model(
        self,
        model: RegisterModel | None,
        *,
        selected_register_index: int | None = None,
    ) -> None:
        self._canvas.set_model(model, selected_register_index=selected_register_index)
        self._canvas.setFixedSize(self._canvas.sizeHint())

    def set_selected_register(self, register_index: int | None) -> None:
        """Highlight one register without emitting ``register_selected``."""
        self._canvas.set_selected_register(register_index)


class _AddressMapCanvas(QWidget):
    """Paint register blocks on a vertical byte-offset timeline."""

    register_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._timeline: AddressTimeline | None = None
        self._selected_register_index: int | None = None

    @property
    def selected_register_index(self) -> int | None:
        return self._selected_register_index

    def sizeHint(self) -> QSize:
        height = self._content_height()
        width = (
            AddressMapWidget._MARGIN * 2
            + AddressMapWidget._RULER_WIDTH
            + AddressMapWidget._LANE_WIDTH
        )
        return QSize(width, height)

    def set_model(
        self,
        model: RegisterModel | None,
        *,
        selected_register_index: int | None = None,
    ) -> None:
        self._timeline = build_address_timeline(model) if model is not None else None
        if selected_register_index is not None:
            self._selected_register_index = selected_register_index
        elif self._timeline is None:
            self._selected_register_index = None
        elif self._selected_register_index is not None:
            valid = {register.register_index for register in self._timeline.registers}
            if self._selected_register_index not in valid:
                self._selected_register_index = None
        self.update()

    def set_selected_register(self, register_index: int | None) -> None:
        if self._selected_register_index == register_index:
            return
        self._selected_register_index = register_index
        self.update()

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#fafafa"))
        if self._timeline is None:
            painter.setPen(QColor("#666666"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Address map appears here for the active bank.",
            )
            return

        lane = self._lane_rect()
        self._paint_gaps(painter, lane, self._timeline.gaps)
        for register in self._timeline.registers:
            self._paint_register(painter, lane, register)
        self._paint_ruler(painter, lane)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._timeline is None:
            return
        lane = self._lane_rect()
        point = event.position().toPoint()
        if not lane.contains(point):
            return
        register_index = self._register_at_point(point.x(), point.y(), lane)
        if register_index is None:
            return
        self._selected_register_index = register_index
        self.update()
        self.register_selected.emit(register_index)

    def _content_height(self) -> int:
        if self._timeline is None:
            return 160
        slot_count = (self._timeline.byte_high + 4 - self._timeline.byte_low) // 4
        lane_height = max(
            min_register_block_height() * 2,
            slot_count * AddressMapWidget.pixels_per_slot(),
        )
        return AddressMapWidget._MARGIN * 2 + lane_height

    def _paint_gaps(
        self, painter: QPainter, lane: QRect, gaps: list[AddressGap]
    ) -> None:
        painter.setPen(QColor("#999999"))
        painter.drawRect(lane)
        for gap in gaps:
            rect = self._span_rect(gap.start, gap.end, lane)
            painter.fillRect(rect, QColor("#e6e6e6"))
            painter.setPen(QColor("#bbbbbb"))
            painter.drawRect(rect)
            painter.setPen(QColor("#999999"))

    def _paint_register(
        self,
        painter: QPainter,
        lane: QRect,
        register: TimelineRegister,
    ) -> None:
        rect = self._register_rect(register.start, register.end, lane)
        if register.conflict:
            fill = QColor("#f5c2c7")
            border = QColor("#b02a37")
        elif register.register_index == self._selected_register_index:
            fill = QColor("#9ec5fe")
            border = QColor("#3366aa")
        elif register.hw_access == "external":
            fill = QColor("#ffe69c")
            border = QColor("#997404")
        else:
            fill = QColor("#cfe2ff")
            border = QColor("#3366aa")

        painter.fillRect(rect, fill)
        painter.setPen(border)
        painter.drawRect(rect)
        painter.setPen(QColor("#222222"))
        painter.setFont(_register_label_font())
        text_rect = rect.adjusted(
            AddressMapWidget._TEXT_PADDING,
            AddressMapWidget._TEXT_PADDING,
            -AddressMapWidget._TEXT_PADDING,
            -AddressMapWidget._TEXT_PADDING,
        )
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            register_timeline_label(register),
        )

    def _paint_ruler(self, painter: QPainter, lane: QRect) -> None:
        if self._timeline is None:
            return
        painter.setPen(QColor("#444444"))
        painter.setFont(_ruler_label_font())
        tick_height = QFontMetrics(_ruler_label_font()).height() + 4
        for tick in timeline_ruler_ticks(self._timeline):
            y = self._offset_y(tick.paint_offset, lane)
            painter.drawLine(lane.left() - 4, y, lane.left(), y)
            painter.drawText(
                AddressMapWidget._MARGIN,
                y - tick_height // 2,
                AddressMapWidget._RULER_WIDTH - 6,
                tick_height,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                format_ruler_tick_label(tick),
            )

    def _register_at_point(self, x: int, y: int, lane: QRect) -> int | None:
        if self._timeline is None:
            return None
        for register in reversed(self._timeline.registers):
            rect = self._register_rect(register.start, register.end, lane)
            if rect.contains(x, y):
                return register.register_index
        return None

    def _lane_rect(self) -> QRect:
        height = self._content_height() - AddressMapWidget._MARGIN * 2
        return QRect(
            AddressMapWidget._MARGIN + AddressMapWidget._RULER_WIDTH,
            AddressMapWidget._MARGIN,
            AddressMapWidget._LANE_WIDTH,
            max(1, height),
        )

    def _span_rect(self, start: int, end: int, lane: QRect) -> QRect:
        top = self._offset_y(end + 4, lane)
        bottom = self._offset_y(start, lane)
        return QRect(
            lane.left(),
            top,
            lane.width(),
            max(4, bottom - top),
        )

    def _register_rect(self, start: int, end: int, lane: QRect) -> QRect:
        rect = self._span_rect(start, end, lane)
        min_height = min_register_block_height()
        if rect.height() >= min_height:
            return rect
        return QRect(
            rect.left(),
            rect.bottom() - min_height,
            rect.width(),
            min_height,
        )

    def _offset_y(self, byte_offset: int, lane: QRect) -> int:
        assert self._timeline is not None
        span = max(4, self._timeline.byte_high + 4 - self._timeline.byte_low)
        ratio = (byte_offset - self._timeline.byte_low) / span
        return lane.bottom() - int(ratio * lane.height())
