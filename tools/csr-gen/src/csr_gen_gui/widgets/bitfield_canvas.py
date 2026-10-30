"""32-bit register bitfield canvas with drag-to-move, resize, and create."""

from __future__ import annotations

from csr_gen.model import Register, register_has_address_range
from csr_gen_gui.bitfield_editing import (
    REGISTER_BITS,
    RULER_MAJOR_BITS,
    BitGap,
    BitSlice,
    CalloutLabelSpec,
    bit_boundary_x,
    bit_in_gap,
    callout_band_height,
    field_block_colors,
    fields_to_slices,
    find_bit_gaps,
    format_access_label,
    format_field_bit_range,
    layout_callout_labels,
    normalize_drag_bits,
    ruler_tick_rise,
    try_create_field,
    try_delete_field,
    try_update_field_access,
    try_update_field_bits,
)
from csr_gen_gui.table_editing import ACCESS_CHOICES

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QResizeEvent,
)
from PySide6.QtWidgets import QMenu, QWidget


class BitfieldCanvas(QWidget):
    """Paint one register's fields and support structural edits."""

    fields_changed = Signal(list)
    edit_rejected = Signal(str)
    field_selected = Signal(object)

    _MARGIN = 8
    _RULER_HEIGHT = 22
    _LANE_HEIGHT = 48
    _CALLOUT_GAP = 6
    _CALLOUT_ROW_HEIGHT = 14
    _DELETE_SIZE = 14
    _EDGE_HIT = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._register: Register | None = None
        self._slices: list[BitSlice] = []
        self._gaps: list[BitGap] = []
        self._active_field_index: int | None = None
        self._drag_mode: str | None = None
        self._drag_start_x = 0
        self._drag_start_msb = 0
        self._drag_start_lsb = 0
        self._create_anchor_bit: int | None = None
        self._create_msb: int | None = None
        self._create_lsb: int | None = None
        self.setMinimumHeight(self._content_height(row_count=1))
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)

    def _content_height(self, *, row_count: int) -> int:
        return (
            self._MARGIN * 2
            + self._RULER_HEIGHT
            + self._LANE_HEIGHT
            + callout_band_height(
                row_count=row_count,
                row_height=self._CALLOUT_ROW_HEIGHT,
                gap=self._CALLOUT_GAP,
            )
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_minimum_height()

    def _update_minimum_height(self) -> None:
        row_count = self._estimate_callout_row_count()
        height = self._content_height(row_count=max(row_count, 1))
        if self.minimumHeight() != height:
            self.setMinimumHeight(height)

    def _estimate_callout_row_count(self) -> int:
        if not self._slices or self._register is None:
            return 0
        lane = self._lane_rect()
        _, row_count = self._build_callout_layout(lane, QFont("Sans Serif", 8))
        return row_count

    def _build_callout_layout(
        self,
        lane: QRect,
        font: QFont,
    ) -> tuple[list, int]:
        from PySide6.QtGui import QFontMetrics

        metrics = QFontMetrics(font)
        specs = []
        for slice_ in self._slices:
            rect = self._slice_rect(slice_.msb, slice_.lsb, lane)
            specs.append(
                CalloutLabelSpec(
                    field_index=slice_.index,
                    anchor_x=rect.center().x(),
                    label_width=metrics.horizontalAdvance(slice_.name),
                )
            )
        return layout_callout_labels(
            specs,
            lane_left=lane.left(),
            lane_right=lane.right(),
        )

    def set_register(self, register: Register | None) -> None:
        self._register = register
        self._clear_drag_state()
        if register is None or register_has_address_range(register):
            self._slices = []
            self._gaps = []
        else:
            self._slices = fields_to_slices(register.fields)
            self._gaps = find_bit_gaps(register.fields)
        self._active_field_index = None
        self._update_minimum_height()
        self.update()

    @property
    def selected_field_index(self) -> int | None:
        return self._active_field_index

    def set_selected_field(self, field_index: int | None) -> None:
        """Highlight one field without emitting ``field_selected``."""
        if self._active_field_index == field_index:
            return
        self._active_field_index = field_index
        self.update()

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#fafafa"))
        if self._register is None:
            painter.setPen(QColor("#666666"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Select a register to edit its bitfields.",
            )
            return
        if register_has_address_range(self._register):
            painter.setPen(QColor("#666666"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Ranged external registers are edited with the address-range wizard.",
            )
            return

        lane = self._lane_rect()
        painter.setPen(QColor("#999999"))
        painter.drawRect(lane)
        self._draw_bit_grid(painter, lane)

        for gap in self._gaps:
            rect = self._slice_rect(gap.msb, gap.lsb, lane)
            painter.fillRect(rect, QColor("#e6e6e6"))
            painter.setPen(QColor("#bbbbbb"))
            painter.drawRect(rect)

        if not self._slices:
            painter.setPen(QColor("#666666"))
            painter.drawText(
                lane,
                Qt.AlignmentFlag.AlignCenter,
                "Drag in the lane to create the first field.",
            )

        if self._create_msb is not None and self._create_lsb is not None:
            preview = self._slice_rect(self._create_msb, self._create_lsb, lane)
            painter.fillRect(preview, QColor("#d4edda"))
            painter.setPen(QColor("#28a745"))
            painter.drawRect(preview)

        for slice_ in self._slices:
            self._draw_field_block(painter, slice_, lane)

        self._draw_bit_ruler(painter, lane)
        self._draw_name_callouts(painter, lane)

    def contextMenuEvent(self, event) -> None:
        if self._register is None or register_has_address_range(self._register):
            return
        lane = self._lane_rect()
        if not lane.contains(event.pos()):
            return
        bit = self._x_to_bit(event.pos().x(), lane)
        for slice_ in self._slices:
            if slice_.lsb <= bit <= slice_.msb:
                self._show_field_context_menu(slice_.index, event.globalPos())
                return

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._register is None or register_has_address_range(self._register):
            return
        if event.button() == Qt.MouseButton.RightButton:
            return
        lane = self._lane_rect()
        if not lane.contains(event.position().toPoint()):
            return

        point = event.position().toPoint()
        bit = self._x_to_bit(point.x(), lane)

        for slice_ in self._slices:
            if slice_.index != self._active_field_index:
                continue
            rect = self._slice_rect(slice_.msb, slice_.lsb, lane)
            if self._delete_button_rect(rect).contains(point):
                self._delete_field(slice_.index)
                return

        for slice_ in self._slices:
            if slice_.lsb <= bit <= slice_.msb:
                self._active_field_index = slice_.index
                rect = self._slice_rect(slice_.msb, slice_.lsb, lane)
                edge = self._EDGE_HIT
                if abs(point.x() - rect.left()) <= edge:
                    self._drag_mode = "resize_msb"
                elif abs(point.x() - rect.right()) <= edge:
                    self._drag_mode = "resize_lsb"
                else:
                    self._drag_mode = "move"
                self._drag_start_x = point.x()
                self._drag_start_msb = slice_.msb
                self._drag_start_lsb = slice_.lsb
                self._update_cursor(self._drag_mode)
                self.update()
                self.field_selected.emit(slice_.index)
                return

        if bit_in_gap(self._gaps, bit):
            self._active_field_index = None
            self._drag_mode = "create"
            self._create_anchor_bit = bit
            self._create_msb = bit
            self._create_lsb = bit
            self._drag_start_x = point.x()
            self._update_cursor("create")
            self.update()
            self.field_selected.emit(None)
            return

        self._active_field_index = None
        self.update()
        self.field_selected.emit(None)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._register is None or register_has_address_range(self._register):
            return
        point = event.position().toPoint()

        if self._drag_mode is not None:
            self._update_cursor(self._drag_mode)
            lane = self._lane_rect()
            current_bit = self._x_to_bit(int(event.position().x()), lane)

            if self._drag_mode == "create":
                if self._create_anchor_bit is None:
                    return
                msb, lsb = normalize_drag_bits(self._create_anchor_bit, current_bit)
                self._create_msb = msb
                self._create_lsb = lsb
                self.update()
                return

            if self._active_field_index is None:
                return

            delta_bits = current_bit - self._x_to_bit(self._drag_start_x, lane)
            msb = self._drag_start_msb
            lsb = self._drag_start_lsb
            width = msb - lsb
            if self._drag_mode == "move":
                msb = min(
                    REGISTER_BITS - 1,
                    max(width, self._drag_start_msb + delta_bits),
                )
                lsb = msb - width
            elif self._drag_mode == "resize_msb":
                msb = min(
                    REGISTER_BITS - 1,
                    max(lsb, self._drag_start_msb + delta_bits),
                )
            elif self._drag_mode == "resize_lsb":
                lsb = max(0, min(msb, self._drag_start_lsb + delta_bits))
            self._preview_update(self._active_field_index, msb, lsb)
            return

        self._update_cursor(self._hit_test(point))

    def leaveEvent(self, event) -> None:
        self.unsetCursor()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_mode is None or self._register is None:
            self._update_cursor(self._hit_test(event.position().toPoint()))
            return

        if self._drag_mode == "create":
            self._finish_create()
            self._update_cursor(self._hit_test(event.position().toPoint()))
            return

        self._drag_mode = None
        if self._active_field_index is None:
            self._update_cursor(self._hit_test(event.position().toPoint()))
            return
        slice_ = self._slices[self._active_field_index]
        updated, error = try_update_field_bits(
            self._register.fields,
            self._active_field_index,
            msb=slice_.msb,
            lsb=slice_.lsb,
        )
        if error or updated is None:
            self.edit_rejected.emit(error or "Edit rejected.")
            self.set_register(self._register)
            self._update_cursor(self._hit_test(event.position().toPoint()))
            return
        self.fields_changed.emit(updated)
        self._update_cursor(self._hit_test(event.position().toPoint()))

    def _draw_field_block(
        self, painter: QPainter, slice_: BitSlice, lane: QRect
    ) -> None:
        rect = self._slice_rect(slice_.msb, slice_.lsb, lane)
        selected = slice_.index == self._active_field_index
        fill_hex, border_hex = field_block_colors(slice_.access, selected=selected)
        painter.fillRect(rect, QColor(fill_hex))
        painter.setPen(QColor(border_hex))
        painter.drawRect(rect)

        inner = rect.adjusted(2, 2, -2, -2)
        painter.setFont(QFont("Sans Serif", 7, QFont.Weight.Bold))
        painter.drawText(
            inner,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            format_access_label(slice_.access).upper(),
        )
        painter.setFont(QFont("Monospace", 7))
        painter.drawText(
            inner,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
            format_field_bit_range(slice_.msb, slice_.lsb),
        )
        if selected:
            self._draw_delete_button(painter, rect)

    def _draw_name_callouts(self, painter: QPainter, lane: QRect) -> None:
        if not self._slices:
            return
        font = QFont("Sans Serif", 8)
        painter.setFont(font)
        placements, row_count = self._build_callout_layout(lane, font)
        if row_count <= 0:
            return

        callout_top = lane.bottom() + self._CALLOUT_GAP
        slices_by_index = {slice_.index: slice_ for slice_ in self._slices}

        for placement in placements:
            slice_ = slices_by_index[placement.field_index]
            row_top = callout_top + placement.row * self._CALLOUT_ROW_HEIGHT
            row_mid_y = row_top + self._CALLOUT_ROW_HEIGHT // 2
            label_center_x = placement.label_x + placement.label_width // 2

            painter.setPen(QColor("#888888"))
            if abs(label_center_x - placement.anchor_x) <= 1:
                painter.drawLine(
                    placement.anchor_x,
                    lane.bottom(),
                    placement.anchor_x,
                    row_mid_y,
                )
            else:
                drop_y = row_top
                painter.drawLine(
                    placement.anchor_x,
                    lane.bottom(),
                    placement.anchor_x,
                    drop_y,
                )
                painter.drawLine(
                    placement.anchor_x,
                    drop_y,
                    label_center_x,
                    drop_y,
                )
                painter.drawLine(
                    label_center_x,
                    drop_y,
                    label_center_x,
                    row_mid_y,
                )

            selected = placement.field_index == self._active_field_index
            painter.setPen(QColor("#222222" if selected else "#444444"))
            painter.drawText(
                placement.label_x,
                row_top,
                placement.label_width,
                self._CALLOUT_ROW_HEIGHT,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                slice_.name,
            )

    def _hit_test(self, point: QPoint) -> str | None:
        """Return hover/drag mode for one point in the lane."""
        if self._register is None or register_has_address_range(self._register):
            return None
        lane = self._lane_rect()
        if not lane.contains(point):
            return None
        bit = self._x_to_bit(point.x(), lane)

        for slice_ in self._slices:
            if slice_.index != self._active_field_index:
                continue
            rect = self._slice_rect(slice_.msb, slice_.lsb, lane)
            if self._delete_button_rect(rect).contains(point):
                return "delete"

        for slice_ in self._slices:
            if slice_.lsb <= bit <= slice_.msb:
                rect = self._slice_rect(slice_.msb, slice_.lsb, lane)
                if abs(point.x() - rect.left()) <= self._EDGE_HIT:
                    return "resize_msb"
                if abs(point.x() - rect.right()) <= self._EDGE_HIT:
                    return "resize_lsb"
                return "move"

        if bit_in_gap(self._gaps, bit):
            return "create"
        return None

    def _update_cursor(self, mode: str | None) -> None:
        if mode in {"resize_msb", "resize_lsb"}:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif mode == "move":
            cursor = (
                Qt.CursorShape.ClosedHandCursor
                if self._drag_mode == "move"
                else Qt.CursorShape.OpenHandCursor
            )
            self.setCursor(cursor)
        elif mode == "create":
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif mode == "delete":
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.unsetCursor()

    def _finish_create(self) -> None:
        self._drag_mode = None
        if (
            self._register is None
            or self._create_msb is None
            or self._create_lsb is None
        ):
            self._clear_create_preview()
            return
        updated, error = try_create_field(
            self._register.fields,
            msb=self._create_msb,
            lsb=self._create_lsb,
        )
        self._clear_create_preview()
        if error or updated is None:
            self.edit_rejected.emit(error or "Could not create field.")
            return
        new_index = len(updated) - 1
        self.fields_changed.emit(updated)
        self._active_field_index = new_index
        self.field_selected.emit(new_index)
        self.update()

    def _delete_field(self, field_index: int) -> None:
        if self._register is None:
            return
        updated, error = try_delete_field(self._register.fields, field_index)
        if error or updated is None:
            self.edit_rejected.emit(error or "Could not delete field.")
            return
        self.fields_changed.emit(updated)
        self._active_field_index = None
        self.field_selected.emit(None)

    def _set_field_access(self, field_index: int, access: str) -> None:
        if self._register is None:
            return
        updated, error = try_update_field_access(
            self._register.fields,
            field_index,
            access,
        )
        if error or updated is None:
            self.edit_rejected.emit(error or "Could not update access.")
            return
        self.fields_changed.emit(updated)
        self._active_field_index = field_index
        self.field_selected.emit(field_index)

    def _show_field_context_menu(self, field_index: int, global_pos: QPoint) -> None:
        self._active_field_index = field_index
        self.field_selected.emit(field_index)
        self.update()

        menu = QMenu(self)
        access_menu = menu.addMenu("Set access")
        for access in ACCESS_CHOICES:
            action = access_menu.addAction(access.upper())
            action.triggered.connect(
                lambda _checked=False, value=access: self._set_field_access(
                    field_index,
                    value,
                )
            )
        delete_action = menu.addAction("Delete field")
        delete_action.triggered.connect(
            lambda: self._delete_field(field_index),
        )
        menu.exec(global_pos)

    def _draw_delete_button(self, painter: QPainter, slice_rect: QRect) -> None:
        button = self._delete_button_rect(slice_rect)
        painter.fillRect(button, QColor("#ffffff"))
        painter.setPen(QColor("#aa3333"))
        painter.drawRect(button)
        painter.drawLine(button.topLeft(), button.bottomRight())
        painter.drawLine(button.topRight(), button.bottomLeft())

    def _delete_button_rect(self, slice_rect: QRect) -> QRect:
        return QRect(
            slice_rect.right() - self._DELETE_SIZE + 1,
            slice_rect.top(),
            self._DELETE_SIZE,
            self._DELETE_SIZE,
        )

    def _clear_drag_state(self) -> None:
        self._drag_mode = None
        self._clear_create_preview()

    def _clear_create_preview(self) -> None:
        self._create_anchor_bit = None
        self._create_msb = None
        self._create_lsb = None

    def _preview_update(self, field_index: int, msb: int, lsb: int) -> None:
        if self._register is None:
            return
        updated, error = try_update_field_bits(
            self._register.fields,
            field_index,
            msb=msb,
            lsb=lsb,
        )
        if error or updated is None:
            return
        self._register = Register(
            name=self._register.name,
            address=self._register.address,
            description=self._register.description,
            hw_access=self._register.hw_access,
            address_end=self._register.address_end,
            fields=updated,
        )
        self._slices = fields_to_slices(updated)
        self._gaps = find_bit_gaps(updated)
        self._update_minimum_height()
        self.update()

    def _draw_bit_grid(self, painter: QPainter, lane: QRect) -> None:
        painter.setPen(QColor("#e8e8e8"))
        for bit in range(REGISTER_BITS):
            x = self._bit_x(bit, lane)
            painter.drawLine(x, lane.top(), x, lane.bottom())
        painter.drawLine(lane.right(), lane.top(), lane.right(), lane.bottom())

    def _draw_bit_ruler(self, painter: QPainter, lane: QRect) -> None:
        painter.setFont(QFont("Monospace", 8))
        for bit in range(REGISTER_BITS):
            x = self._bit_x(bit, lane)
            rise = ruler_tick_rise(bit)
            if bit in RULER_MAJOR_BITS:
                painter.setPen(QColor("#444444"))
                painter.drawLine(x, lane.top() - rise, x, lane.top())
                painter.drawText(
                    x - 8,
                    self._MARGIN,
                    16,
                    self._RULER_HEIGHT,
                    Qt.AlignmentFlag.AlignHCenter,
                    str(bit),
                )
            else:
                painter.setPen(QColor("#aaaaaa"))
                painter.drawLine(x, lane.top() - rise, x, lane.top())

    def _lane_rect(self) -> QRect:
        return QRect(
            self._MARGIN,
            self._MARGIN + self._RULER_HEIGHT,
            max(1, self.width() - 2 * self._MARGIN),
            self._LANE_HEIGHT,
        )

    def _bit_x(self, bit: int, lane: QRect) -> int:
        return bit_boundary_x(bit, lane_left=lane.left(), lane_width=lane.width())

    def _x_to_bit(self, x: int, lane: QRect) -> int:
        ratio = (x - lane.left()) / max(1, lane.width())
        bit = REGISTER_BITS - 1 - int(ratio * REGISTER_BITS)
        return max(0, min(REGISTER_BITS - 1, bit))

    def _slice_rect(self, msb: int, lsb: int, lane: QRect) -> QRect:
        left = self._bit_x(msb, lane)
        right = self._bit_x(lsb, lane)
        return QRect(left, lane.top(), max(4, right - left + 1), lane.height())
