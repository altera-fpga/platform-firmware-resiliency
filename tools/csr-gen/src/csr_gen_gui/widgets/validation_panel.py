"""Read-only validation message pane for the GUI."""

from __future__ import annotations

from csr_gen_gui.validation_display import ValidationMessage, format_validation_html

from PySide6.QtWidgets import QTextEdit

__all__ = ["ValidationPanel"]


class ValidationPanel(QTextEdit):
    """Validation output with colored INFO/WARNING/ERROR prefixes."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Validation messages appear here.")

    def set_messages(self, messages: list[ValidationMessage]) -> None:
        if not messages:
            self.clear()
            return
        self.setHtml(format_validation_html(messages))
