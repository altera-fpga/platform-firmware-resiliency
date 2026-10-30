"""Qt undo commands for the CSR GUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from csr_gen_gui.editor_snapshot import EditorSnapshot

from PySide6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from csr_gen_gui.main_window import MainWindow


class RestoreEditorSnapshotCommand(QUndoCommand):
    """Undo command that restores a captured editor snapshot."""

    def __init__(
        self,
        before: EditorSnapshot,
        after: EditorSnapshot,
        text: str,
        window: MainWindow,
    ) -> None:
        super().__init__(text)
        self._before = before
        self._after = after
        self._window = window

    def undo(self) -> None:
        self._window._restore_editor_snapshot(self._before)

    def redo(self) -> None:
        self._window._restore_editor_snapshot(self._after)
