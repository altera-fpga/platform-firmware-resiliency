"""Capture and restore GUI editor state for undo/redo."""

from __future__ import annotations

import copy
from dataclasses import dataclass

from csr_gen_gui.document import DocumentController
from csr_gen_gui.models import Document


def _normalize_rows(
    rows: list[dict[str, str]],
) -> tuple[tuple[tuple[str, str], ...], ...]:
    return tuple(tuple(sorted(row.items())) for row in rows)


@dataclass(frozen=True)
class EditorSnapshot:
    """One undo/redo checkpoint for the CSR editor."""

    document: Document
    table_rows: tuple[tuple[tuple[str, str], ...], ...]
    collapsed_registers: frozenset[int]
    document_title: str
    selected_register_index: int
    selected_field_index: int | None


def capture_editor_snapshot(
    controller: DocumentController,
    *,
    table_rows: list[dict[str, str]],
    collapsed_registers: set[int] | frozenset[int],
    document_title: str,
    selected_register_index: int,
    selected_field_index: int | None,
) -> EditorSnapshot:
    """Return a deep copy of the editable document and UI selection state."""
    return EditorSnapshot(
        document=copy.deepcopy(controller.document),
        table_rows=_normalize_rows(table_rows),
        collapsed_registers=frozenset(collapsed_registers),
        document_title=document_title,
        selected_register_index=selected_register_index,
        selected_field_index=selected_field_index,
    )


def restore_controller_snapshot(
    controller: DocumentController,
    snapshot: EditorSnapshot,
) -> list[dict[str, str]]:
    """Restore ``controller`` from ``snapshot`` and return active-bank table rows."""
    controller.document = copy.deepcopy(snapshot.document)
    controller.document.document_title = snapshot.document_title or None
    return [dict(row) for row in snapshot.table_rows]


def snapshots_equal(left: EditorSnapshot, right: EditorSnapshot) -> bool:
    """Return whether two snapshots describe the same editable state."""
    return left == right
