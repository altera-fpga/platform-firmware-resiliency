"""Primary window for the csr-gen Markdown CSR editor."""

from __future__ import annotations

from pathlib import Path

from csr_gen.errors import CsrValidationError, ModelValidationError
from csr_gen.model import Field, register_has_address_range
from csr_gen_gui.bitfield_editing import (
    try_update_field_access,
    try_update_field_reset,
)
from csr_gen_gui.document import DEFAULT_INTERFACE_TYPE, DocumentController
from csr_gen_gui.editor_snapshot import (
    EditorSnapshot,
    capture_editor_snapshot,
    restore_controller_snapshot,
    snapshots_equal,
)
from csr_gen_gui.undo_commands import RestoreEditorSnapshotCommand
from csr_gen_gui.import_export import (
    EXPORT_DIALOG_OPTIONS,
    ExportFormat,
    default_export_filename,
    export_bank_file,
    import_bank_from_csv,
    import_bank_from_ipxact,
    import_bank_from_systemrdl,
    ipxact_import_selector_names,
    systemrdl_import_selector_names,
    validate_bank_for_export,
)
from csr_gen_gui.model_table import model_to_row_dicts, row_dicts_to_model
from csr_gen_gui.preview_panes import PREVIEW_PANE_SPECS
from csr_gen_gui.range_wizard import RangeRegisterWizard
from csr_gen_gui.syntax_highlighting import PreviewLanguage
from csr_gen_gui.table_editing import sort_table_rows, table_rows_need_sort
from csr_gen_gui.widgets.address_map_widget import AddressMapWidget
from csr_gen_gui.widgets.bitfield_canvas import BitfieldCanvas
from csr_gen_gui.widgets.bitfield_inspector import BitfieldFieldInspector
from csr_gen_gui.widgets.code_preview import CodePreviewEdit
from csr_gen_gui.validation_display import (
    messages_from_errors,
    validation_error,
    validation_info,
)
from csr_gen_gui.widgets.csr_table_widget import CsrTableWidget
from csr_gen_gui.widgets.validation_panel import ValidationPanel

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction, QCloseEvent, QFont, QKeySequence, QUndoStack
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

_INTERFACE_TYPES = ["axi4-lite", "avalon-mm", "axi4", "apb"]
_PREVIEW_FONT = QFont("Courier", 10)


class MainWindow(QMainWindow):
    """CSR bank editor with validation and artifact previews."""

    def __init__(self) -> None:
        super().__init__()
        self._controller = DocumentController()
        self._path: Path | None = None
        self._dirty = False
        self._selected_register_index = 0
        self._selected_field_index: int | None = None
        self._syncing_selection = False
        self._restoring_undo = False
        self._title_edit_snapshot: EditorSnapshot | None = None
        self._undo_stack = QUndoStack(self)
        self._undo_anchor = capture_editor_snapshot(
            self._controller,
            table_rows=[],
            collapsed_registers=frozenset(),
            document_title="",
            selected_register_index=0,
            selected_field_index=None,
        )

        self.setWindowTitle("csr-gen")
        self.resize(1400, 900)

        self._document_title = QLineEdit()
        self._document_title.setPlaceholderText("Document title (optional H1)")
        self._document_title.textChanged.connect(self._mark_dirty)
        self._document_title.installEventFilter(self)

        self._bank_list = QListWidget()
        self._bank_list.currentRowChanged.connect(self._on_bank_selected)

        self._table = CsrTableWidget()
        self._table.rows_changed.connect(self._on_table_changed)
        self._table.selection_changed.connect(self._on_table_selection_changed)

        self._bitfield = BitfieldCanvas()
        self._bitfield.fields_changed.connect(self._on_bitfield_fields_changed)
        self._bitfield.edit_rejected.connect(self._on_bitfield_rejected)
        self._bitfield.field_selected.connect(self._on_bitfield_field_selected)

        self._bitfield_inspector = BitfieldFieldInspector()
        self._bitfield_inspector.access_changed.connect(
            self._on_bitfield_inspector_access_changed
        )
        self._bitfield_inspector.reset_changed.connect(
            self._on_bitfield_inspector_reset_changed
        )
        self._bitfield_inspector.reset_rejected.connect(self._on_bitfield_rejected)

        self._address_map = AddressMapWidget()
        self._address_map.register_selected.connect(
            self._on_address_map_register_selected
        )

        self._validation = ValidationPanel()

        self._interface_type = QComboBox()
        self._interface_type.addItems(_INTERFACE_TYPES)
        self._interface_type.setCurrentText(DEFAULT_INTERFACE_TYPE)
        self._interface_type.currentTextChanged.connect(self._refresh_previews)

        self._preview_widgets = {
            "systemverilog": CodePreviewEdit(
                PreviewLanguage.SYSTEMVERILOG,
                font=_PREVIEW_FONT,
            ),
            "c_header": CodePreviewEdit(PreviewLanguage.C_LIKE, font=_PREVIEW_FONT),
            "dml": CodePreviewEdit(PreviewLanguage.C_LIKE, font=_PREVIEW_FONT),
            "systemrdl": CodePreviewEdit(PreviewLanguage.SYSTEMRDL, font=_PREVIEW_FONT),
            "ipxact": CodePreviewEdit(PreviewLanguage.XML, font=_PREVIEW_FONT),
        }

        self._preview_tabs = QTabWidget()
        self._preview_pane_tab_indexes: dict[str, int] = {}
        for spec in PREVIEW_PANE_SPECS:
            index = self._preview_tabs.addTab(
                self._preview_widgets[spec.pane_id],
                spec.tab_label,
            )
            self._preview_pane_tab_indexes[spec.pane_id] = index

        self._preview_header = QWidget()
        preview_header_layout = QHBoxLayout(self._preview_header)
        preview_header_layout.setContentsMargins(0, 0, 0, 0)
        preview_header_layout.addWidget(QLabel("Interface type"))
        preview_header_layout.addWidget(self._interface_type)
        preview_header_layout.addStretch()

        self._preview_panel = QWidget()
        preview_layout = QVBoxLayout(self._preview_panel)
        preview_layout.addWidget(self._preview_header)
        preview_layout.addWidget(self._preview_tabs)

        bank_buttons = QWidget()
        bank_button_layout = QHBoxLayout(bank_buttons)
        bank_button_layout.setContentsMargins(0, 0, 0, 0)
        add_bank = QPushButton("Add bank")
        add_bank.clicked.connect(self._add_bank)
        rename_bank = QPushButton("Rename")
        rename_bank.clicked.connect(self._rename_bank)
        remove_bank = QPushButton("Remove")
        remove_bank.clicked.connect(self._remove_bank)
        bank_button_layout.addWidget(add_bank)
        bank_button_layout.addWidget(rename_bank)
        bank_button_layout.addWidget(remove_bank)

        bank_panel = QWidget()
        bank_layout = QVBoxLayout(bank_panel)
        bank_layout.addWidget(QLabel("CSR banks"))
        bank_layout.addWidget(self._bank_list)
        bank_layout.addWidget(bank_buttons)

        editor_panel = QWidget()
        editor_layout = QVBoxLayout(editor_panel)
        editor_layout.addWidget(self._document_title)
        table_header = QWidget()
        table_header_layout = QHBoxLayout(table_header)
        table_header_layout.setContentsMargins(0, 0, 0, 0)
        table_header_layout.addWidget(QLabel("Register table"))
        table_header_layout.addStretch()
        self._sort_table_button = QPushButton("Sort")
        self._sort_table_button.setToolTip(
            "Sort registers by address and fields by bit index (lowest first)."
        )
        self._sort_table_button.clicked.connect(self._sort_register_table)
        table_header_layout.addWidget(self._sort_table_button)
        editor_layout.addWidget(table_header)
        editor_layout.addWidget(self._table)
        editor_layout.addWidget(QLabel("Bitfield editor"))
        editor_layout.addWidget(self._bitfield)
        editor_layout.addWidget(self._bitfield_inspector)
        editor_layout.addWidget(QLabel("Address map"))
        editor_layout.addWidget(self._address_map)

        center_split = QSplitter(Qt.Orientation.Vertical)
        center_split.addWidget(editor_panel)
        validation_wrapper = QWidget()
        validation_layout = QVBoxLayout(validation_wrapper)
        validation_layout.addWidget(QLabel("Validation"))
        validation_layout.addWidget(self._validation)
        center_split.addWidget(validation_wrapper)
        center_split.setStretchFactor(0, 4)
        center_split.setStretchFactor(1, 1)

        root_split = QSplitter(Qt.Orientation.Horizontal)
        root_split.addWidget(bank_panel)
        root_split.addWidget(center_split)
        root_split.addWidget(self._preview_panel)
        root_split.setStretchFactor(0, 1)
        root_split.setStretchFactor(1, 4)
        root_split.setStretchFactor(2, 2)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(root_split)
        self.setCentralWidget(container)

        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self._new_document()

    def _build_actions(self) -> None:
        self._action_new = QAction("&New", self)
        self._action_new.setShortcut(QKeySequence.StandardKey.New)
        self._action_new.triggered.connect(self._new_document)

        self._action_open = QAction("&Open…", self)
        self._action_open.setShortcut(QKeySequence.StandardKey.Open)
        self._action_open.triggered.connect(self._open_document)

        self._action_save = QAction("&Save", self)
        self._action_save.setShortcut(QKeySequence.StandardKey.Save)
        self._action_save.triggered.connect(self._save_document)

        self._action_save_as = QAction("Save &as…", self)
        self._action_save_as.triggered.connect(self._save_document_as)

        self._action_import_ipxact = QAction("From &IP-XACT…", self)
        self._action_import_ipxact.triggered.connect(self._import_ipxact)

        self._action_import_systemrdl = QAction("From &SystemRDL…", self)
        self._action_import_systemrdl.triggered.connect(self._import_systemrdl)

        self._action_import_csv = QAction("From &CSV…", self)
        self._action_import_csv.triggered.connect(self._import_csv)

        self._action_export_sv = QAction("To &SystemVerilog…", self)
        self._action_export_sv.triggered.connect(
            lambda: self._export_active_bank(ExportFormat.SYSTEMVERILOG)
        )

        self._action_export_c = QAction("To &C Header…", self)
        self._action_export_c.triggered.connect(
            lambda: self._export_active_bank(ExportFormat.C_HEADER)
        )

        self._action_export_dml = QAction("To &DML…", self)
        self._action_export_dml.triggered.connect(
            lambda: self._export_active_bank(ExportFormat.DML)
        )

        self._action_export_ipxact = QAction("To IP-XAC&T…", self)
        self._action_export_ipxact.triggered.connect(
            lambda: self._export_active_bank(ExportFormat.IPXACT)
        )

        self._action_export_rdl = QAction("To System&RDL…", self)
        self._action_export_rdl.triggered.connect(
            lambda: self._export_active_bank(ExportFormat.SYSTEMRDL)
        )

        self._action_export_csv = QAction("To CS&V…", self)
        self._action_export_csv.triggered.connect(
            lambda: self._export_active_bank(ExportFormat.CSV)
        )

        self._action_undo = QAction("&Undo", self)
        self._action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._action_undo.triggered.connect(self._undo_stack.undo)
        self._action_undo.setEnabled(False)

        self._action_redo = QAction("&Redo", self)
        self._action_redo.setShortcuts(
            [QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")]
        )
        self._action_redo.triggered.connect(self._undo_stack.redo)
        self._action_redo.setEnabled(False)

        self._undo_stack.canUndoChanged.connect(self._update_undo_actions)
        self._undo_stack.canRedoChanged.connect(self._update_undo_actions)
        self._undo_stack.undoTextChanged.connect(self._on_undo_text_changed)
        self._undo_stack.redoTextChanged.connect(self._on_redo_text_changed)

        self._action_add_register = QAction("Add &register row", self)
        self._action_add_register.triggered.connect(self._add_register_row)

        self._action_add_field = QAction("Add &field row", self)
        self._action_add_field.triggered.connect(self._add_field_row)

        self._action_delete_rows = QAction("&Delete selected", self)
        self._action_delete_rows.setShortcut(QKeySequence.StandardKey.Delete)
        self._action_delete_rows.triggered.connect(self._table.delete_selected)

        self._action_sort_table = QAction("Sort register &table", self)
        self._action_sort_table.triggered.connect(self._sort_register_table)

        self._action_add_range = QAction("Add external address &range…", self)
        self._action_add_range.triggered.connect(self._add_range_register)

        self._action_quit = QAction("&Quit", self)
        self._action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self._action_quit.triggered.connect(self.close)

        self._preview_pane_actions: dict[str, QAction] = {}
        for spec in PREVIEW_PANE_SPECS:
            action = QAction(spec.menu_label, self)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(
                lambda checked, pane_id=spec.pane_id: self._set_preview_pane_visible(
                    pane_id,
                    checked,
                )
            )
            self._preview_pane_actions[spec.pane_id] = action

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self._action_new)
        file_menu.addAction(self._action_open)
        file_menu.addSeparator()
        import_menu = file_menu.addMenu("&Import")
        import_menu.addAction(self._action_import_ipxact)
        import_menu.addAction(self._action_import_systemrdl)
        import_menu.addAction(self._action_import_csv)
        export_menu = file_menu.addMenu("Export &Active Bank")
        export_menu.addAction(self._action_export_sv)
        export_menu.addAction(self._action_export_c)
        export_menu.addAction(self._action_export_dml)
        export_menu.addAction(self._action_export_ipxact)
        export_menu.addAction(self._action_export_rdl)
        export_menu.addAction(self._action_export_csv)
        file_menu.addSeparator()
        file_menu.addAction(self._action_save)
        file_menu.addAction(self._action_save_as)
        file_menu.addSeparator()
        file_menu.addAction(self._action_quit)

        edit_menu = self.menuBar().addMenu("&Edit")
        edit_menu.addAction(self._action_undo)
        edit_menu.addAction(self._action_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self._action_add_register)
        edit_menu.addAction(self._action_add_field)
        edit_menu.addAction(self._action_delete_rows)
        edit_menu.addSeparator()
        edit_menu.addAction(self._action_sort_table)
        edit_menu.addAction(self._action_add_range)

        view_menu = self.menuBar().addMenu("&View")
        preview_menu = view_menu.addMenu("&Preview Panes")
        for spec in PREVIEW_PANE_SPECS:
            preview_menu.addAction(self._preview_pane_actions[spec.pane_id])

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)
        toolbar.addAction(self._action_new)
        toolbar.addAction(self._action_open)
        toolbar.addAction(self._action_save)
        toolbar.addSeparator()
        toolbar.addAction(self._action_add_register)
        toolbar.addAction(self._action_add_field)
        toolbar.addAction(self._action_add_range)

    def _set_preview_pane_visible(self, pane_id: str, visible: bool) -> None:
        index = self._preview_pane_tab_indexes[pane_id]
        self._preview_tabs.setTabVisible(index, visible)
        self._update_preview_panel_layout()

    def _update_preview_panel_layout(self) -> None:
        any_visible = any(
            action.isChecked() for action in self._preview_pane_actions.values()
        )
        self._preview_panel.setVisible(any_visible)
        sv_visible = self._preview_pane_actions["systemverilog"].isChecked()
        self._preview_header.setVisible(any_visible and sv_visible)
        if not any_visible:
            return
        current = self._preview_tabs.currentIndex()
        if self._preview_tabs.isTabVisible(current):
            return
        for index in range(self._preview_tabs.count()):
            if self._preview_tabs.isTabVisible(index):
                self._preview_tabs.setCurrentIndex(index)
                break

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    def _new_document(self) -> None:
        if not self._confirm_discard():
            return
        self._controller.new_document()
        self._controller.add_bank("CSR Registers")
        self._path = None
        self._document_title.clear()
        self._dirty = False
        self._reload_banks()
        self._reset_undo_history()
        self._update_window_title()

    def _open_document(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open CSR Markdown",
            str(self._path.parent if self._path else Path.cwd()),
            "Markdown (*.md);;All files (*)",
        )
        if not path:
            return
        self.open_document_path(Path(path))

    def open_document_path(
        self,
        path: Path,
        *,
        confirm_discard: bool = True,
    ) -> bool:
        """Load a Markdown CSR file into the editor."""
        if confirm_discard and not self._confirm_discard():
            return False
        try:
            self._controller.load(path)
        except Exception as error:
            QMessageBox.critical(self, "Open failed", str(error))
            return False
        if not self._controller.document.banks:
            QMessageBox.warning(
                self,
                "No CSR banks",
                "No CSR bank sections (## headings with CSR tables) were found "
                "in this file.",
            )
            return False
        self._path = path
        self._document_title.setText(self._controller.document.document_title or "")
        self._dirty = False
        self._reload_banks()
        self._reset_undo_history()
        self._update_window_title()
        return True

    def _save_document(self) -> None:
        if self._path is None:
            self._save_document_as()
            return
        self._save_to_path(self._path)

    def _save_document_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSR Markdown",
            str(self._path or Path.cwd() / "regs.md"),
            "Markdown (*.md);;All files (*)",
        )
        if not path:
            return
        self._save_to_path(Path(path))

    def _save_to_path(self, path: Path) -> None:
        if not self._sync_table_to_active_bank():
            return
        title = self._document_title.text().strip()
        self._controller.document.document_title = title or None
        try:
            self._controller.save(path)
        except (ModelValidationError, CsrValidationError, ValueError) as error:
            QMessageBox.critical(self, "Save failed", str(error))
            self._refresh_validation_and_previews()
            return
        self._path = path
        self._dirty = False
        self._update_window_title()

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Unsaved changes",
            "Discard unsaved changes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _mark_dirty(self) -> None:
        self._dirty = True
        self._update_window_title()

    def eventFilter(self, obj, event) -> bool:
        if obj is self._document_title and not self._restoring_undo:
            if event.type() == QEvent.Type.FocusIn:
                self._title_edit_snapshot = self._capture_snapshot()
            elif event.type() == QEvent.Type.FocusOut:
                if self._title_edit_snapshot is not None:
                    after = self._capture_snapshot()
                    self._push_undo(
                        self._title_edit_snapshot,
                        after,
                        "Edit document title",
                    )
                    self._title_edit_snapshot = None
        return super().eventFilter(obj, event)

    def _capture_snapshot(self) -> EditorSnapshot:
        if self._controller.document.banks:
            self._sync_table_to_active_bank(show_errors=False, refresh=False)
        return capture_editor_snapshot(
            self._controller,
            table_rows=(
                self._table.all_rows if self._controller.document.banks else []
            ),
            collapsed_registers=self._table.collapsed_registers,
            document_title=self._document_title.text(),
            selected_register_index=self._selected_register_index,
            selected_field_index=self._selected_field_index,
        )

    def _push_undo(
        self,
        before: EditorSnapshot,
        after: EditorSnapshot,
        description: str,
    ) -> None:
        if self._restoring_undo or snapshots_equal(before, after):
            self._undo_anchor = after
            return
        self._undo_stack.push(
            RestoreEditorSnapshotCommand(before, after, description, self)
        )
        self._undo_anchor = after

    def _reset_undo_history(self) -> None:
        self._undo_stack.clear()
        self._undo_anchor = self._capture_snapshot()

    def _restore_editor_snapshot(self, snapshot: EditorSnapshot) -> None:
        self._restoring_undo = True
        try:
            table_rows = restore_controller_snapshot(self._controller, snapshot)
            self._document_title.blockSignals(True)
            self._document_title.setText(snapshot.document_title)
            self._document_title.blockSignals(False)

            self._bank_list.blockSignals(True)
            self._bank_list.clear()
            for bank in self._controller.document.banks:
                self._bank_list.addItem(bank.section_heading)
            active = self._controller.document.active_bank_index
            if self._controller.document.banks:
                self._bank_list.setCurrentRow(active)
            self._bank_list.blockSignals(False)

            self._selected_register_index = snapshot.selected_register_index
            self._selected_field_index = snapshot.selected_field_index

            if self._controller.document.banks:
                self._table.load_rows(table_rows)
                self._table.set_collapsed_registers(snapshot.collapsed_registers)
                model, _errors = row_dicts_to_model(table_rows, allow_incomplete=True)
                if model is not None:
                    self._controller.active_bank.model = model
            else:
                self._table.load_rows([])
                self._table.set_collapsed_registers(set())

            self._refresh_register_views()
            self._refresh_validation_and_previews()
            self._update_sort_table_enabled()
            self._update_add_field_enabled()

            self._syncing_selection = True
            try:
                if (
                    self._controller.document.banks
                    and self._controller.active_bank.model.registers
                ):
                    if self._selected_field_index is not None:
                        self._table.select_field_row(
                            self._selected_register_index,
                            self._selected_field_index,
                        )
                    else:
                        self._table.select_register_row(self._selected_register_index)
            finally:
                self._syncing_selection = False

            self._mark_dirty()
            self._undo_anchor = snapshot
        finally:
            self._restoring_undo = False

    def _update_undo_actions(self) -> None:
        self._action_undo.setEnabled(self._undo_stack.canUndo())
        self._action_redo.setEnabled(self._undo_stack.canRedo())

    def _on_undo_text_changed(self, text: str) -> None:
        self._action_undo.setText(f"&Undo {text}" if text else "&Undo")

    def _on_redo_text_changed(self, text: str) -> None:
        self._action_redo.setText(f"&Redo {text}" if text else "&Redo")

    def _update_window_title(self) -> None:
        name = self._path.name if self._path else "Untitled"
        prefix = f"{name}*" if self._dirty else name
        self.setWindowTitle(f"{prefix} — csr-gen")

    def _reload_banks(self) -> None:
        self._bank_list.blockSignals(True)
        self._bank_list.clear()
        for bank in self._controller.document.banks:
            self._bank_list.addItem(bank.section_heading)
        active = self._controller.document.active_bank_index
        self._bank_list.setCurrentRow(active)
        self._bank_list.blockSignals(False)
        self._load_active_bank_table()

    def _on_bank_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._controller.document.banks):
            return
        if row == self._controller.document.active_bank_index:
            return
        if not self._sync_table_to_active_bank(show_errors=False):
            self._bank_list.blockSignals(True)
            self._bank_list.setCurrentRow(self._controller.document.active_bank_index)
            self._bank_list.blockSignals(False)
            return
        self._controller.set_active_bank(row)
        self._load_active_bank_table()

    def _load_active_bank_table(self) -> None:
        if not self._controller.document.banks:
            self._table.load_rows([])
            self._refresh_validation_and_previews()
            self._update_sort_table_enabled()
            self._update_add_field_enabled()
            return
        rows = model_to_row_dicts(self._controller.active_bank.model)
        self._table.load_rows(rows)
        self._selected_register_index = 0
        self._selected_field_index = None
        self._refresh_register_views()
        self._refresh_validation_and_previews()
        self._update_sort_table_enabled()
        self._update_add_field_enabled()

    def _update_add_field_enabled(self) -> None:
        selection = self._table.current_selection()
        enabled = False
        if selection is not None and self._controller.document.banks:
            register_index, _field_index = selection
            model = self._controller.active_bank.model
            if 0 <= register_index < len(model.registers):
                register = model.registers[register_index]
                enabled = not register_has_address_range(register)
        self._action_add_field.setEnabled(enabled)

    def _update_sort_table_enabled(self) -> None:
        enabled = bool(self._controller.document.banks) and table_rows_need_sort(
            self._table.all_rows
        )
        self._action_sort_table.setEnabled(enabled)
        self._sort_table_button.setEnabled(enabled)

    def _sort_register_table(self) -> None:
        if not self._controller.document.banks:
            return
        rows = self._table.all_rows
        if not table_rows_need_sort(rows):
            return

        before = self._capture_snapshot()

        selected_register_name: str | None = None
        selected_field_name: str | None = None
        model = self._controller.active_bank.model
        if model.registers:
            register_index = min(
                self._selected_register_index,
                len(model.registers) - 1,
            )
            register = model.registers[register_index]
            selected_register_name = register.name
            if (
                self._selected_field_index is not None
                and 0 <= self._selected_field_index < len(register.fields)
            ):
                selected_field_name = register.fields[self._selected_field_index].name

        self._table.load_rows(sort_table_rows(rows))
        self._mark_dirty()
        if not self._sync_table_to_active_bank(show_errors=True, refresh=False):
            self._update_sort_table_enabled()
            return

        if selected_register_name is not None:
            for index, register in enumerate(
                self._controller.active_bank.model.registers,
            ):
                if register.name == selected_register_name:
                    self._selected_register_index = index
                    self._selected_field_index = None
                    if selected_field_name is not None:
                        for field_index, field in enumerate(register.fields):
                            if field.name == selected_field_name:
                                self._selected_field_index = field_index
                                break
                    break

        self._update_sort_table_enabled()
        self._refresh_register_views()
        self._syncing_selection = True
        try:
            if self._selected_field_index is not None:
                self._table.select_field_row(
                    self._selected_register_index,
                    self._selected_field_index,
                )
            elif self._controller.active_bank.model.registers:
                self._table.select_register_row(self._selected_register_index)
        finally:
            self._syncing_selection = False
        self._refresh_validation_and_previews(
            status_message="Register table sorted.",
        )
        after = self._capture_snapshot()
        self._push_undo(before, after, "Sort register table")

    def _sync_table_to_active_bank(
        self,
        *,
        show_errors: bool = True,
        refresh: bool = True,
    ) -> bool:
        if not self._controller.document.banks:
            return True
        model, errors = row_dicts_to_model(
            self._table.all_rows,
            allow_incomplete=True,
        )
        if model is None:
            if show_errors:
                self._validation.set_messages(messages_from_errors(errors))
            return False
        self._controller.active_bank.model = model
        if refresh:
            self._refresh_register_views()
            self._refresh_validation_and_previews()
        elif show_errors and errors:
            self._validation.set_messages(messages_from_errors(errors))
        return not errors

    def _on_table_changed(self) -> None:
        before = self._undo_anchor
        self._mark_dirty()
        self._sync_table_to_active_bank(show_errors=True)
        self._update_sort_table_enabled()
        after = self._capture_snapshot()
        if not self._restoring_undo:
            self._push_undo(before, after, "Edit table")
        else:
            self._undo_anchor = after

    def _on_table_selection_changed(
        self, register_index: int, field_index: int
    ) -> None:
        if self._syncing_selection:
            return
        self._selected_register_index = register_index
        self._selected_field_index = None if field_index < 0 else field_index
        self._refresh_register_views()
        self._update_add_field_enabled()

    def _on_bitfield_field_selected(self, field_index: object) -> None:
        if self._syncing_selection or not self._controller.document.banks:
            return
        if not isinstance(field_index, int):
            self._selected_field_index = None
        else:
            self._selected_field_index = field_index
        self._update_bitfield_inspector()
        if not isinstance(field_index, int):
            return
        self._syncing_selection = True
        try:
            self._table.select_field_row(self._selected_register_index, field_index)
        finally:
            self._syncing_selection = False

    def _on_address_map_register_selected(self, register_index: int) -> None:
        if self._syncing_selection:
            return
        self._selected_register_index = register_index
        self._selected_field_index = None
        self._syncing_selection = True
        try:
            self._table.select_register_row(register_index)
        finally:
            self._syncing_selection = False
        self._refresh_register_views()

    def _refresh_register_views(self) -> None:
        if not self._controller.document.banks:
            self._bitfield.set_register(None)
            self._address_map.set_model(None)
            self._update_bitfield_inspector()
            return
        model = self._controller.active_bank.model
        index = (
            min(self._selected_register_index, len(model.registers) - 1)
            if model.registers
            else 0
        )
        self._address_map.set_model(
            model,
            selected_register_index=index if model.registers else None,
        )
        if not model.registers:
            self._bitfield.set_register(None)
            self._update_bitfield_inspector()
            return
        index = min(self._selected_register_index, len(model.registers) - 1)
        register = model.registers[index]
        if self._selected_field_index is not None and (
            self._selected_field_index < 0
            or self._selected_field_index >= len(register.fields)
        ):
            self._selected_field_index = None
        self._bitfield.set_register(register)
        self._bitfield.set_selected_field(self._selected_field_index)
        self._update_bitfield_inspector()

    def _update_bitfield_inspector(self) -> None:
        if not self._controller.document.banks:
            self._bitfield_inspector.set_field(None)
            return
        model = self._controller.active_bank.model
        if not model.registers:
            self._bitfield_inspector.set_field(None)
            return
        index = min(self._selected_register_index, len(model.registers) - 1)
        register = model.registers[index]
        if self._selected_field_index is None:
            self._bitfield_inspector.set_field(None)
            return
        if self._selected_field_index < 0 or self._selected_field_index >= len(
            register.fields
        ):
            self._bitfield_inspector.set_field(None)
            return
        self._bitfield_inspector.set_field(register.fields[self._selected_field_index])

    def _on_bitfield_inspector_access_changed(self, access: str) -> None:
        if self._selected_field_index is None or not self._controller.document.banks:
            return
        before = self._capture_snapshot()
        model = self._controller.active_bank.model
        if not model.registers:
            return
        index = min(self._selected_register_index, len(model.registers) - 1)
        register = model.registers[index]
        updated, error = try_update_field_access(
            register.fields,
            self._selected_field_index,
            access,
        )
        if error or updated is None:
            self._validation.set_messages(
                [validation_error(error or "Could not update access.")]
            )
            self._update_bitfield_inspector()
            return
        register.fields = updated
        self._table.load_rows(model_to_row_dicts(model))
        self._mark_dirty()
        self._sync_table_to_active_bank(show_errors=True)
        self._update_bitfield_inspector()
        after = self._capture_snapshot()
        self._push_undo(before, after, "Change field access")

    def _on_bitfield_inspector_reset_changed(self, reset: int) -> None:
        if self._selected_field_index is None or not self._controller.document.banks:
            return
        before = self._capture_snapshot()
        model = self._controller.active_bank.model
        if not model.registers:
            return
        index = min(self._selected_register_index, len(model.registers) - 1)
        register = model.registers[index]
        updated, error = try_update_field_reset(
            register.fields,
            self._selected_field_index,
            reset,
        )
        if error or updated is None:
            self._validation.set_messages(
                [validation_error(error or "Could not update reset.")]
            )
            self._update_bitfield_inspector()
            return
        register.fields = updated
        self._table.load_rows(model_to_row_dicts(model))
        self._mark_dirty()
        self._sync_table_to_active_bank(show_errors=True)
        self._update_bitfield_inspector()
        after = self._capture_snapshot()
        self._push_undo(before, after, "Change field reset")

    def _on_bitfield_fields_changed(self, fields: list[Field]) -> None:
        if not self._controller.document.banks:
            return
        before = self._capture_snapshot()
        model = self._controller.active_bank.model
        index = min(self._selected_register_index, len(model.registers) - 1)
        register = model.registers[index]
        register.fields = fields
        self._table.load_rows(model_to_row_dicts(model))
        self._mark_dirty()
        self._sync_table_to_active_bank(show_errors=True)
        self._update_bitfield_inspector()
        after = self._capture_snapshot()
        self._push_undo(before, after, "Edit bitfield")

    def _on_bitfield_rejected(self, message: str) -> None:
        self._validation.set_messages([validation_error(message)])

    def _refresh_validation_and_previews(
        self,
        *,
        status_message: str | None = None,
    ) -> None:
        if not self._controller.document.banks:
            self._validation.clear()
            for widget in self._preview_widgets.values():
                widget.clear()
            return
        errors = self._controller.validate_active_bank()
        previews = self._controller.generate_previews(
            interface_type=self._interface_type.currentText()
        )
        messages = []
        if status_message:
            messages.append(validation_info(status_message))
        if errors:
            messages.extend(messages_from_errors(errors))
        elif previews.errors:
            messages.extend(messages_from_errors(previews.errors))
        else:
            messages.append(validation_info("No validation errors."))
        self._validation.set_messages(messages)
        preview_text = {
            "systemverilog": previews.systemverilog or "",
            "c_header": previews.c_header or "",
            "dml": previews.dml or "",
            "systemrdl": previews.systemrdl or "",
            "ipxact": previews.ipxact or "",
        }
        for pane_id, widget in self._preview_widgets.items():
            widget.setPlainText(preview_text[pane_id])

    def _refresh_previews(self) -> None:
        self._refresh_validation_and_previews()

    def _add_bank(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            "Add CSR bank",
            "Section heading:",
            text="CSR Registers",
        )
        if not ok or not name.strip():
            return
        if not self._sync_table_to_active_bank():
            return
        before = self._capture_snapshot()
        self._controller.add_bank(name.strip())
        self._mark_dirty()
        self._reload_banks()
        after = self._capture_snapshot()
        self._push_undo(before, after, "Add bank")

    def _rename_bank(self) -> None:
        row = self._bank_list.currentRow()
        if row < 0:
            return
        current = self._controller.document.banks[row].section_heading
        name, ok = QInputDialog.getText(
            self,
            "Rename CSR bank",
            "Section heading:",
            text=current,
        )
        if not ok or not name.strip():
            return
        before = self._capture_snapshot()
        self._controller.rename_bank(row, name.strip())
        self._bank_list.item(row).setText(name.strip())
        self._mark_dirty()
        self._refresh_validation_and_previews()
        after = self._capture_snapshot()
        self._push_undo(before, after, "Rename bank")

    def _remove_bank(self) -> None:
        row = self._bank_list.currentRow()
        if row < 0:
            return
        if len(self._controller.document.banks) == 1:
            QMessageBox.warning(self, "Remove bank", "At least one bank is required.")
            return
        answer = QMessageBox.question(
            self,
            "Remove bank",
            f"Remove bank {self._controller.document.banks[row].section_heading!r}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        before = self._capture_snapshot()
        self._controller.remove_bank(row)
        self._mark_dirty()
        self._reload_banks()
        after = self._capture_snapshot()
        self._push_undo(before, after, "Remove bank")

    def _add_register_row(self) -> None:
        from csr_gen_gui.table_editing import (
            RowKind,
            build_row_infos,
            insert_register_row,
        )

        rows = insert_register_row(self._table.all_rows, len(self._table.all_rows))
        new_register_index = 0
        for info in build_row_infos(rows):
            if info.kind == RowKind.REGISTER:
                new_register_index = info.register_index
        self._table.load_rows(rows)
        self._selected_register_index = new_register_index
        self._selected_field_index = None
        self._on_table_changed()
        self._table.select_register_row(new_register_index)

    def _add_field_row(self) -> None:
        from csr_gen_gui.table_editing import field_insert_row_index, insert_field_row

        selection = self._table.current_selection()
        if selection is None:
            return
        register_index, field_index = selection
        insert_at = field_insert_row_index(
            self._table.all_rows,
            register_index=register_index,
            field_index=field_index,
        )
        if insert_at is None:
            return
        rows = insert_field_row(self._table.all_rows, insert_at)
        self._table.load_rows(rows)
        self._on_table_changed()

    def _add_range_register(self) -> None:
        dialog = RangeRegisterWizard(self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.register is None:
            return
        if not self._sync_table_to_active_bank(show_errors=False):
            QMessageBox.warning(
                self,
                "Fix validation errors",
                "Fix table validation errors before adding a ranged register.",
            )
            return
        before = self._capture_snapshot()
        self._controller.active_bank.model.registers.append(dialog.register)
        self._load_active_bank_table()
        self._mark_dirty()
        after = self._capture_snapshot()
        self._push_undo(before, after, "Add address range register")

    def _prepare_for_import(self) -> bool:
        return self._confirm_discard()

    def _choose_import_selector(
        self,
        *,
        title: str,
        label: str,
        choices: list[str],
    ) -> str | None:
        choice, ok = QInputDialog.getItem(
            self,
            title,
            label,
            choices,
            0,
            False,
        )
        if not ok or not choice:
            return None
        return str(choice)

    def _finalize_import(self) -> None:
        self._path = None
        self._document_title.clear()
        self._dirty = True
        self._reload_banks()
        self._reset_undo_history()
        self._update_window_title()

    def _import_ipxact(self) -> None:
        if not self._prepare_for_import():
            return
        path_text, _ = QFileDialog.getOpenFileName(
            self,
            "Import IP-XACT",
            str(self._path.parent if self._path else Path.cwd()),
            "IP-XACT XML (*.xml);;All files (*)",
        )
        if not path_text:
            return
        path = Path(path_text)
        try:
            selector_names = ipxact_import_selector_names(path)
            address_block_name = None
            if selector_names is not None:
                address_block_name = self._choose_import_selector(
                    title="Select IP-XACT address block",
                    label="Address block:",
                    choices=selector_names,
                )
                if address_block_name is None:
                    return
            bank = import_bank_from_ipxact(
                path,
                address_block_name=address_block_name,
            )
            self._controller.import_bank(bank)
        except Exception as error:
            QMessageBox.critical(self, "Import failed", str(error))
            return
        self._finalize_import()

    def _import_systemrdl(self) -> None:
        if not self._prepare_for_import():
            return
        path_text, _ = QFileDialog.getOpenFileName(
            self,
            "Import SystemRDL",
            str(self._path.parent if self._path else Path.cwd()),
            "SystemRDL (*.rdl);;All files (*)",
        )
        if not path_text:
            return
        path = Path(path_text)
        try:
            selector_names = systemrdl_import_selector_names(path)
            addrmap_instance = None
            if selector_names is not None:
                addrmap_instance = self._choose_import_selector(
                    title="Select SystemRDL addrmap",
                    label="Addrmap instance:",
                    choices=selector_names,
                )
                if addrmap_instance is None:
                    return
            bank = import_bank_from_systemrdl(
                path,
                addrmap_instance=addrmap_instance,
            )
            self._controller.import_bank(bank)
        except Exception as error:
            QMessageBox.critical(self, "Import failed", str(error))
            return
        self._finalize_import()

    def _import_csv(self) -> None:
        if not self._prepare_for_import():
            return
        path_text, _ = QFileDialog.getOpenFileName(
            self,
            "Import CSV",
            str(self._path.parent if self._path else Path.cwd()),
            "CSV (*.csv);;All files (*)",
        )
        if not path_text:
            return
        path = Path(path_text)
        section_heading, ok = QInputDialog.getText(
            self,
            "Import CSV",
            "Section heading:",
            text=path.stem,
        )
        if not ok or not section_heading.strip():
            return
        try:
            bank = import_bank_from_csv(path, section_heading=section_heading.strip())
            self._controller.import_bank(bank)
        except Exception as error:
            QMessageBox.critical(self, "Import failed", str(error))
            return
        self._finalize_import()

    def _export_active_bank(self, export_format: ExportFormat) -> None:
        if not self._controller.document.banks:
            QMessageBox.warning(self, "Export", "Add a CSR bank before exporting.")
            return
        if not self._sync_table_to_active_bank():
            return
        errors = validate_bank_for_export(self._controller.active_bank.model)
        if errors:
            QMessageBox.warning(
                self,
                "Export blocked",
                "Fix validation errors in the active bank before exporting.",
            )
            self._validation.set_messages(messages_from_errors(errors))
            return

        dialog = EXPORT_DIALOG_OPTIONS[export_format]
        default_dir = self._path.parent if self._path else Path.cwd()
        default_name = default_export_filename(
            self._controller.active_bank.section_heading,
            export_format,
        )
        path_text, _ = QFileDialog.getSaveFileName(
            self,
            dialog.title,
            str(default_dir / default_name),
            f"{dialog.filter};;All files (*)",
        )
        if not path_text:
            return
        path = Path(path_text)
        try:
            export_bank_file(
                self._controller.active_bank,
                path,
                export_format,
                interface_type=self._interface_type.currentText(),
            )
        except (ModelValidationError, CsrValidationError, ValueError) as error:
            QMessageBox.critical(self, "Export failed", str(error))
            return
        QMessageBox.information(
            self,
            "Export complete",
            f"Wrote {path.name}",
        )


def create_main_window() -> MainWindow:
    """Return the configured main window."""
    return MainWindow()
