"""CSR register table with Phase 2 editing affordances."""

from __future__ import annotations

from csr_gen_gui.model_table import (
    TABLE_COLUMNS,
    dict_to_table_row,
)
from csr_gen_gui.table_editing import (
    ACCESS_CHOICES,
    COL_ACCESS,
    COL_ADDRESS,
    COL_DESCRIPTION,
    COL_HW_ACCESS,
    COL_REGISTER,
    COL_RESET,
    HW_ACCESS_CHOICES,
    RowKind,
    TableRowInfo,
    build_row_infos,
    delete_field_row,
    delete_register,
    expand_indicator,
    expand_register,
    field_insert_actions,
    insert_field_row,
    insert_register_row,
    commit_table_cell,
    read_row_values,
    register_cell_text,
    strip_register_indicator,
    toggle_register_collapsed,
    visible_field_row_index,
    visible_register_row_index,
    visible_row_infos,
)

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QMenu,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QStyleOptionViewItem,
    QWidget,
)


class _ComboDelegate(QStyledItemDelegate):
    def __init__(
        self,
        choices: tuple[str, ...],
        *,
        enabled_for_row,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._choices = choices
        self._enabled_for_row = enabled_for_row

    def createEditor(
        self,
        parent: QWidget,
        _option: QStyleOptionViewItem,
        index,
    ):
        if not self._enabled_for_row(index.row()):
            return None
        combo = QComboBox(parent)
        combo.addItems(list(self._choices))
        return combo

    def setEditorData(self, editor: QWidget, index) -> None:
        combo = editor
        if not isinstance(combo, QComboBox):
            return
        value = index.model().data(index, Qt.ItemDataRole.EditRole) or ""
        combo.setCurrentText(str(value))

    def setModelData(self, editor: QWidget, model, index) -> None:
        combo = editor
        if not isinstance(combo, QComboBox):
            return
        model.setData(index, combo.currentText(), Qt.ItemDataRole.EditRole)


class CsrTableWidget(QTableWidget):
    """Editable CSR table with collapse, combo columns, and context menu."""

    rows_changed = Signal()
    register_selected = Signal(int)
    selection_changed = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, len(TABLE_COLUMNS), parent)
        self._loading = False
        self._block_selection_signals = False
        self._all_rows: list[dict[str, str]] = []
        self._row_infos: list[TableRowInfo] = []
        self._collapsed_registers: set[int] = set()
        self._visible_infos: list[TableRowInfo] = []

        self.setHorizontalHeaderLabels(list(TABLE_COLUMNS))
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)
        self.cellChanged.connect(self._on_cell_changed)
        self.cellClicked.connect(self._on_cell_clicked)
        self.itemSelectionChanged.connect(self._on_selection_changed)

        self.setItemDelegateForColumn(
            COL_ACCESS,
            _ComboDelegate(
                ACCESS_CHOICES,
                enabled_for_row=self._is_field_row,
                parent=self,
            ),
        )
        self.setItemDelegateForColumn(
            COL_HW_ACCESS,
            _ComboDelegate(
                HW_ACCESS_CHOICES,
                enabled_for_row=self._is_register_row,
                parent=self,
            ),
        )

    @property
    def all_rows(self) -> list[dict[str, str]]:
        return [dict(row) for row in self._all_rows]

    @property
    def collapsed_registers(self) -> frozenset[int]:
        return frozenset(self._collapsed_registers)

    def set_collapsed_registers(self, collapsed: set[int] | frozenset[int]) -> None:
        """Restore expand/collapse state and refresh visible rows."""
        self._collapsed_registers = set(collapsed)
        self._refresh_display()

    def load_rows(self, rows: list[dict[str, str]]) -> None:
        self._all_rows = [dict(row) for row in rows]
        self._row_infos = build_row_infos(self._all_rows)
        self._refresh_display()

    def _refresh_display(self) -> None:
        self._loading = True
        self._visible_infos = visible_row_infos(
            self._row_infos,
            self._collapsed_registers,
        )
        self.setRowCount(len(self._visible_infos))
        for visible_index, info in enumerate(self._visible_infos):
            values = dict_to_table_row(info.row_dict)
            if info.kind == RowKind.REGISTER:
                collapsed = info.register_index in self._collapsed_registers
                values[COL_REGISTER] = register_cell_text(
                    strip_register_indicator(values[COL_REGISTER])
                    or info.row_dict.get("register", ""),
                    collapsed=collapsed,
                )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    {
                        "kind": info.kind.value,
                        "register_index": info.register_index,
                        "field_index": info.field_index,
                        "full_index": self._full_index(info),
                    },
                )
                if info.kind == RowKind.REGISTER and column not in {
                    COL_REGISTER,
                    COL_ADDRESS,
                    COL_HW_ACCESS,
                    COL_DESCRIPTION,
                }:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if info.kind == RowKind.FIELD and column in {
                    COL_REGISTER,
                    COL_ADDRESS,
                    COL_HW_ACCESS,
                }:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.setItem(visible_index, column, item)
        self._loading = False

    def _full_index(self, info: TableRowInfo) -> int:
        for index, candidate in enumerate(self._row_infos):
            if (
                candidate.kind == info.kind
                and candidate.register_index == info.register_index
                and candidate.field_index == info.field_index
            ):
                return index
        return -1

    def _is_register_row(self, visible_row: int) -> bool:
        if visible_row < 0 or visible_row >= len(self._visible_infos):
            return False
        return self._visible_infos[visible_row].kind == RowKind.REGISTER

    def _is_field_row(self, visible_row: int) -> bool:
        if visible_row < 0 or visible_row >= len(self._visible_infos):
            return False
        return self._visible_infos[visible_row].kind == RowKind.FIELD

    def current_selection(self) -> tuple[int, int | None] | None:
        """Return ``(register_index, field_index)`` for the selected row."""
        row = self.currentRow()
        if row < 0 or row >= len(self._visible_infos):
            return None
        info = self._visible_infos[row]
        if info.kind == RowKind.FIELD:
            assert info.field_index is not None
            return info.register_index, info.field_index
        return info.register_index, None

    def _on_cell_changed(self, visible_row: int, column: int) -> None:
        if self._loading:
            return
        item = self.item(visible_row, column)
        if item is None:
            return
        metadata = item.data(Qt.ItemDataRole.UserRole) or {}
        full_index = metadata.get("full_index", -1)
        if full_index < 0 or full_index >= len(self._all_rows):
            return
        values = [
            (
                self.item(visible_row, col).text()
                if self.item(visible_row, col) is not None
                else ""
            )
            for col in range(len(TABLE_COLUMNS))
        ]
        info = self._visible_infos[visible_row]
        row = commit_table_cell(
            read_row_values(values),
            column,
            kind=info.kind,
        )
        self._all_rows[full_index] = row
        if column in {COL_ADDRESS, COL_RESET}:
            cell_key = "address" if column == COL_ADDRESS else "reset"
            normalized = row.get(cell_key, "")
            if item.text() != normalized:
                self._loading = True
                item.setText(normalized)
                self._loading = False
        self._row_infos = build_row_infos(self._all_rows)
        if metadata.get("kind") == RowKind.REGISTER.value and column == COL_REGISTER:
            self._refresh_display()
        self.rows_changed.emit()

    def _on_cell_clicked(self, row: int, column: int) -> None:
        if column != COL_REGISTER or row < 0 or row >= len(self._visible_infos):
            return
        info = self._visible_infos[row]
        if info.kind != RowKind.REGISTER:
            return
        item = self.item(row, column)
        if item is None:
            return
        text = item.text()
        if text.startswith("[+]") or text.startswith("[−]"):
            self._collapsed_registers = toggle_register_collapsed(
                self._collapsed_registers,
                info.register_index,
            )
            self._refresh_display()
            self.register_selected.emit(info.register_index)

    def _on_selection_changed(self) -> None:
        if self._block_selection_signals:
            return
        row = self.currentRow()
        if row < 0 or row >= len(self._visible_infos):
            return
        info = self._visible_infos[row]
        self.register_selected.emit(info.register_index)
        field_index = info.field_index if info.kind == RowKind.FIELD else -1
        self.selection_changed.emit(
            info.register_index, field_index if field_index is not None else -1
        )

    def select_field_row(self, register_index: int, field_index: int) -> bool:
        """Select a field row, expanding its register when collapsed."""
        if register_index in self._collapsed_registers:
            self._collapsed_registers = expand_register(
                self._collapsed_registers,
                register_index,
            )
            self._refresh_display()
        visible_row = visible_field_row_index(
            self._row_infos,
            self._collapsed_registers,
            register_index,
            field_index,
        )
        if visible_row is None:
            return False
        self._block_selection_signals = True
        try:
            self.selectRow(visible_row)
            self.setCurrentCell(visible_row, 0)
        finally:
            self._block_selection_signals = False
        return True

    def select_register_row(self, register_index: int) -> bool:
        """Select a register definition row."""
        visible_row = visible_register_row_index(
            self._row_infos,
            self._collapsed_registers,
            register_index,
        )
        if visible_row is None:
            return False
        self._block_selection_signals = True
        try:
            self.selectRow(visible_row)
            self.setCurrentCell(visible_row, 0)
        finally:
            self._block_selection_signals = False
        return True

    def _open_context_menu(self, position) -> None:
        visible_row = self.rowAt(position.y())
        if visible_row < 0:
            return
        info = self._visible_infos[visible_row]
        full_index = self._full_index(info)
        menu = QMenu(self)

        add_register_above = menu.addAction("Add register above")
        add_register_below = menu.addAction("Add register below")
        menu.addSeparator()
        add_field_above = menu.addAction("Add field above")
        add_field_below = menu.addAction("Add field below")
        menu.addSeparator()
        delete_register_action = menu.addAction("Delete register")
        delete_field_action = menu.addAction("Delete field")
        is_register = info.kind == RowKind.REGISTER
        is_field = info.kind == RowKind.FIELD
        field_actions = field_insert_actions(info, self._row_infos)
        add_field_above.setEnabled(field_actions.above)
        add_field_below.setEnabled(field_actions.below)
        delete_register_action.setEnabled(is_register)
        delete_field_action.setEnabled(is_field)

        chosen = menu.exec(self.viewport().mapToGlobal(position))
        if chosen is None:
            return
        if chosen == add_register_above:
            block_start = min(
                index
                for index, candidate in enumerate(self._row_infos)
                if candidate.register_index == info.register_index
            )
            self._all_rows = insert_register_row(self._all_rows, block_start)
        elif chosen == add_register_below:
            register_index = info.register_index
            block_end = max(
                index + 1
                for index, candidate in enumerate(self._row_infos)
                if candidate.register_index == register_index
            )
            self._all_rows = insert_register_row(self._all_rows, block_end)
        elif chosen == add_field_above:
            self._all_rows = insert_field_row(self._all_rows, full_index)
        elif chosen == add_field_below:
            self._all_rows = insert_field_row(self._all_rows, full_index + 1)
        elif chosen == delete_register_action:
            self._all_rows = delete_register(self._all_rows, info.register_index)
            self._collapsed_registers.discard(info.register_index)
        elif chosen == delete_field_action:
            self._all_rows = delete_field_row(self._all_rows, full_index)

        self._row_infos = build_row_infos(self._all_rows)
        self._refresh_display()
        self.rows_changed.emit()

    def delete_selected(self) -> None:
        selected_rows = sorted(
            {index.row() for index in self.selectedIndexes()},
            reverse=True,
        )
        for visible_row in selected_rows:
            if visible_row < 0 or visible_row >= len(self._visible_infos):
                continue
            info = self._visible_infos[visible_row]
            if info.kind == RowKind.REGISTER:
                self._all_rows = delete_register(self._all_rows, info.register_index)
                self._collapsed_registers.discard(info.register_index)
            else:
                full_index = self._full_index(info)
                self._all_rows = delete_field_row(self._all_rows, full_index)
        self._row_infos = build_row_infos(self._all_rows)
        self._refresh_display()
        self.rows_changed.emit()
