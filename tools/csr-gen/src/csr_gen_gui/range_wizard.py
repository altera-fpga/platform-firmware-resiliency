"""Dialog for creating ranged external memory-style registers."""

from __future__ import annotations

from csr_gen.literals import (
    HexLiteralError,
    normalize_address_text,
    normalize_reset_text,
    parse_hex_literal,
)
from csr_gen.model import Register, SUPPORTED_ACCESS
from csr_gen.names import csr_identifier_error
from csr_gen_gui.model_table import make_ranged_external_register

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)


class RangeRegisterWizard(QDialog):
    """Create an external register spanning an inclusive address range."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add External Address Range")
        self._register: Register | None = None

        self._name = QLineEdit()
        self._name.setPlaceholderText("MEM")
        self._field_name = QLineEdit()
        self._field_name.setPlaceholderText("WINDOW")
        self._address_start = QLineEdit()
        self._address_start.setPlaceholderText("0x20")
        self._address_end = QLineEdit()
        self._address_end.setPlaceholderText("0x2F")
        self._access = QComboBox()
        self._access.addItems(sorted({"rw", "ro", "wo"}))
        self._reset = QLineEdit("0x0")
        self._description = QLineEdit()

        form = QFormLayout()
        form.addRow("Register name", self._name)
        form.addRow("Field name", self._field_name)
        form.addRow("Start address", self._address_start)
        form.addRow("End address", self._address_end)
        form.addRow("Access", self._access)
        form.addRow("Reset", self._reset)
        form.addRow("Description", self._description)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def register(self) -> Register | None:
        return self._register

    def _accept(self) -> None:
        name = self._name.text().strip()
        field_name = self._field_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid input", "Register name is required.")
            return
        for label, value in (("Register", name), ("Field", field_name or name)):
            name_error = csr_identifier_error(value, kind=label)
            if name_error is not None:
                QMessageBox.warning(self, "Invalid input", name_error)
                return
        try:
            address_start = parse_hex_literal(self._address_start.text())
            address_end = parse_hex_literal(self._address_end.text())
            reset = parse_hex_literal(self._reset.text())
        except HexLiteralError as error:
            QMessageBox.warning(self, "Invalid input", str(error))
            return

        self._address_start.setText(normalize_address_text(self._address_start.text()))
        self._address_end.setText(normalize_address_text(self._address_end.text()))
        self._reset.setText(normalize_reset_text(self._reset.text()))

        access = self._access.currentText().strip().lower()
        if access not in SUPPORTED_ACCESS:
            QMessageBox.warning(
                self, "Invalid input", f"Unsupported access {access!r}."
            )
            return

        register = make_ranged_external_register(
            name=name,
            address_start=address_start,
            address_end=address_end,
            field_name=field_name,
            access=access,
            reset=reset,
            description=self._description.text(),
        )
        self._register = register
        self.accept()
