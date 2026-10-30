"""Inspector row for the selected bitfield slice."""

from __future__ import annotations

from csr_gen.literals import HexLiteralError, normalize_reset_text, parse_hex_literal
from csr_gen.model import Field
from csr_gen_gui.bitfield_editing import format_field_reset
from csr_gen_gui.table_editing import ACCESS_CHOICES

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLineEdit, QWidget


class BitfieldFieldInspector(QWidget):
    """Edit access and reset for the field selected in the bitfield canvas."""

    access_changed = Signal(str)
    reset_changed = Signal(int)
    reset_rejected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._loading = False
        self._field: Field | None = None

        self._summary = QLabel("No field selected")
        self._access = QComboBox()
        self._access.addItems(list(ACCESS_CHOICES))
        self._reset = QLineEdit()
        self._reset.setPlaceholderText("0x0")

        form = QFormLayout(self)
        form.addRow("Selected field", self._summary)
        form.addRow("Access", self._access)
        form.addRow("Reset", self._reset)

        self._access.currentTextChanged.connect(self._on_access_changed)
        self._reset.editingFinished.connect(self._on_reset_committed)

        self.set_field(None)

    def set_field(self, field: Field | None) -> None:
        """Load inspector widgets from ``field`` or clear when none is selected."""
        self._loading = True
        self._field = field
        enabled = field is not None
        self._access.setEnabled(enabled)
        self._reset.setEnabled(enabled)
        if field is None:
            self._summary.setText("No field selected")
            self._access.setCurrentIndex(0)
            self._reset.clear()
        else:
            bits = (
                str(field.msb) if field.msb == field.lsb else f"{field.msb}:{field.lsb}"
            )
            self._summary.setText(f"{field.name}  ({bits})")
            self._access.setCurrentText(field.access)
            self._reset.setText(format_field_reset(field))
        self._loading = False

    def _on_access_changed(self, access: str) -> None:
        if self._loading or self._field is None:
            return
        if access == self._field.access:
            return
        self.access_changed.emit(access)

    def _on_reset_committed(self) -> None:
        if self._loading or self._field is None:
            return
        text = self._reset.text().strip()
        if not text:
            self.reset_rejected.emit("Reset must not be empty.")
            self._reset.setText(format_field_reset(self._field))
            return
        try:
            normalized = normalize_reset_text(text)
            reset = parse_hex_literal(normalized)
        except HexLiteralError as error:
            self.reset_rejected.emit(str(error))
            self._reset.setText(format_field_reset(self._field))
            return
        if reset == self._field.reset:
            self._reset.setText(normalized)
            return
        self._reset.setText(normalized)
        self.reset_changed.emit(reset)
