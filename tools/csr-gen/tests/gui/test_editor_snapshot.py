"""Tests for GUI editor snapshot capture and restore."""

from __future__ import annotations

from pathlib import Path

from csr_gen_gui.document import DocumentController
from csr_gen_gui.editor_snapshot import (
    capture_editor_snapshot,
    restore_controller_snapshot,
    snapshots_equal,
)
from csr_gen_gui.model_table import model_to_row_dicts

GOLDEN = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "golden"
    / "example-device"
    / "regs.md"
)


def test_capture_and_restore_active_bank() -> None:
    controller = DocumentController()
    controller.load(GOLDEN)
    original_description = controller.active_bank.model.registers[0].description

    rows = model_to_row_dicts(controller.active_bank.model)
    snapshot = capture_editor_snapshot(
        controller,
        table_rows=rows,
        collapsed_registers=frozenset(),
        document_title="Example",
        selected_register_index=0,
        selected_field_index=None,
    )

    controller.active_bank.model.registers[0].description = "After edit"
    restored_rows = restore_controller_snapshot(controller, snapshot)

    assert controller.document.document_title == "Example"
    assert controller.active_bank.model.registers[0].description == original_description
    assert restored_rows == rows


def test_snapshots_equal_detects_table_change() -> None:
    controller = DocumentController()
    controller.load(GOLDEN)
    rows = model_to_row_dicts(controller.active_bank.model)
    left = capture_editor_snapshot(
        controller,
        table_rows=rows,
        collapsed_registers=frozenset(),
        document_title="",
        selected_register_index=0,
        selected_field_index=None,
    )
    changed_rows = [dict(row) for row in rows]
    changed_rows[0]["description"] = "Changed"
    right = capture_editor_snapshot(
        controller,
        table_rows=changed_rows,
        collapsed_registers=frozenset(),
        document_title="",
        selected_register_index=0,
        selected_field_index=None,
    )
    assert snapshots_equal(left, left)
    assert not snapshots_equal(left, right)
