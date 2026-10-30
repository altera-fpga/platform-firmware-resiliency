"""Headless tests for bitfield create/delete/access/reset helpers."""

from csr_gen.model import Field
from csr_gen_gui.bitfield_editing import (
    bit_in_gap,
    default_field_name,
    find_bit_gaps,
    normalize_drag_bits,
    try_create_field,
    try_delete_field,
    try_update_field_access,
    try_update_field_reset,
)


def _gap_fields() -> list[Field]:
    return [
        Field(name="LOW", msb=3, lsb=0, access="rw", reset=0),
        Field(name="HIGH", msb=31, lsb=16, access="rw", reset=0),
    ]


def test_default_field_name_avoids_collisions() -> None:
    fields = [
        Field(name="FIELD", msb=0, lsb=0, access="rw", reset=0),
        Field(name="FIELD_1", msb=1, lsb=1, access="rw", reset=0),
    ]
    assert default_field_name([]) == "FIELD"
    assert default_field_name(fields) == "FIELD_2"


def test_normalize_drag_bits_orders_msb_lsb() -> None:
    assert normalize_drag_bits(4, 10) == (10, 4)
    assert normalize_drag_bits(10, 4) == (10, 4)


def test_bit_in_gap() -> None:
    gaps = find_bit_gaps(_gap_fields())
    assert bit_in_gap(gaps, 8) is True
    assert bit_in_gap(gaps, 0) is False


def test_try_create_field_in_gap() -> None:
    fields = _gap_fields()
    updated, error = try_create_field(fields, msb=8, lsb=4)
    assert error is None
    assert updated is not None
    assert len(updated) == 3
    assert updated[-1].name == "FIELD"
    assert updated[-1].msb == 8
    assert updated[-1].lsb == 4


def test_try_create_field_in_empty_register() -> None:
    updated, error = try_create_field([], msb=3, lsb=0)
    assert error is None
    assert updated is not None
    assert len(updated) == 1
    assert updated[0].name == "FIELD"


def test_try_create_field_rejects_overlap() -> None:
    fields = _gap_fields()
    updated, error = try_create_field(fields, msb=5, lsb=0)
    assert updated is None
    assert error is not None


def test_try_delete_field() -> None:
    fields = _gap_fields()
    updated, error = try_delete_field(fields, 0)
    assert error is None
    assert updated is not None
    assert len(updated) == 1
    assert updated[0].name == "HIGH"


def test_try_update_field_access() -> None:
    fields = _gap_fields()
    updated, error = try_update_field_access(fields, 0, "ro")
    assert error is None
    assert updated is not None
    assert updated[0].access == "ro"


def test_field_block_colors_distinguish_reserved_and_selected() -> None:
    from csr_gen_gui.bitfield_editing import (
        field_block_colors,
        format_access_label,
        format_field_bit_range,
        is_reserved_field,
    )

    assert is_reserved_field("none") is True
    assert is_reserved_field("rw") is False
    assert format_access_label("rw1c") == "rw1c"
    assert format_field_bit_range(7, 4) == "7:4"
    assert format_field_bit_range(3, 3) == "3"

    rw_fill, _ = field_block_colors("rw", selected=False)
    none_fill, _ = field_block_colors("none", selected=False)
    assert rw_fill != none_fill
    selected_fill, _ = field_block_colors("rw", selected=True)
    assert selected_fill != rw_fill


def test_try_update_field_reset_rejects_out_of_range() -> None:
    fields = [Field(name="X", msb=3, lsb=0, access="rw", reset=0)]
    updated, error = try_update_field_reset(fields, 0, 0x10)
    assert updated is None
    assert error is not None


def test_layout_callout_labels_uses_multiple_rows_for_tight_fields() -> None:
    from csr_gen_gui.bitfield_editing import CalloutLabelSpec, layout_callout_labels

    specs = [
        CalloutLabelSpec(field_index=0, anchor_x=20, label_width=40),
        CalloutLabelSpec(field_index=1, anchor_x=30, label_width=40),
        CalloutLabelSpec(field_index=2, anchor_x=40, label_width=40),
    ]
    placements, row_count = layout_callout_labels(
        specs,
        lane_left=0,
        lane_right=400,
    )
    assert row_count == 3
    assert {placement.row for placement in placements} == {0, 1, 2}


def test_layout_callout_labels_shares_one_row_for_wide_spacing() -> None:
    from csr_gen_gui.bitfield_editing import CalloutLabelSpec, layout_callout_labels

    specs = [
        CalloutLabelSpec(field_index=0, anchor_x=50, label_width=40),
        CalloutLabelSpec(field_index=1, anchor_x=200, label_width=40),
    ]
    placements, row_count = layout_callout_labels(
        specs,
        lane_left=0,
        lane_right=400,
    )
    assert row_count == 1
    assert all(placement.row == 0 for placement in placements)
