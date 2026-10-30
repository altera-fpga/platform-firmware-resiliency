"""Read-only code preview editor with optional syntax highlighting."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QPlainTextEdit

from csr_gen_gui.syntax_highlighting import PreviewLanguage, attach_preview_highlighter


class CodePreviewEdit(QPlainTextEdit):
    """Read-only preview pane for generated source text."""

    def __init__(
        self,
        language: PreviewLanguage = PreviewLanguage.PLAIN,
        *,
        font: QFont | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        if font is not None:
            self.setFont(font)
        self._highlighter = attach_preview_highlighter(self.document(), language)
