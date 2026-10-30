"""Headless tests for Phase 2 GUI helpers."""

from csr_gen.model import Field, Register, RegisterModel
from csr_gen_gui.address_map import (
    build_address_map,
    build_address_timeline,
    find_address_gaps,
    find_conflicting_register_indices,
    format_address_gap,
    format_ruler_tick_label,
    timeline_ruler_ticks,
)
from csr_gen_gui.bitfield_editing import (
    RULER_MAJOR_BITS,
    bit_boundary_x,
    find_bit_gaps,
    ruler_tick_rise,
    try_update_field_bits,
)
from csr_gen_gui.model_table import model_to_row_dicts
from csr_gen_gui.table_editing import (
    RowKind,
    build_row_infos,
    delete_field_row,
    delete_register,
    expand_register,
    field_insert_actions,
    field_insert_row_index,
    insert_field_row,
    register_field_count,
    toggle_register_collapsed,
    visible_field_row_index,
    visible_register_row_index,
    visible_row_infos,
)
from csr_gen_gui.model_table import table_row_to_dict


def _example_rows() -> list[dict[str, str]]:
    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0x00,
                description="Control",
                fields=[
                    Field(name="A", msb=0, lsb=0, access="rw", reset=0),
                    Field(name="B", msb=2, lsb=1, access="rw", reset=0),
                ],
            ),
            Register(
                name="EVENTS",
                address=0x08,
                description="Events",
                fields=[Field(name="P", msb=7, lsb=0, access="rw1c", reset=0)],
            ),
        ]
    )
    return model_to_row_dicts(model)


def test_field_insert_actions_on_field_and_register_rows() -> None:
    rows = _example_rows()
    infos = build_row_infos(rows)
    field_info = infos[1]
    register_info = infos[0]
    assert field_info.kind == RowKind.FIELD
    assert register_info.kind == RowKind.REGISTER

    field_actions = field_insert_actions(field_info, infos)
    assert field_actions.above is True
    assert field_actions.below is True

    register_actions = field_insert_actions(register_info, infos)
    assert register_actions.above is False
    assert register_actions.below is False


def test_field_insert_below_enabled_on_register_without_fields() -> None:
    rows = [
        table_row_to_dict(["CTRL", "0x00", "", "", "", "", "internal", "Control"]),
    ]
    infos = build_row_infos(rows)
    assert register_field_count(infos, 0) == 0

    actions = field_insert_actions(infos[0], infos)
    assert actions.above is False
    assert actions.below is True


def test_field_insert_row_index_targets_selected_register() -> None:
    rows = _example_rows()
    assert field_insert_row_index(rows, register_index=0, field_index=0) == 2
    assert field_insert_row_index(rows, register_index=0, field_index=None) == 3
    assert field_insert_row_index(rows, register_index=1, field_index=None) == 5

    register_only = [
        table_row_to_dict(["CTRL", "0x00", "", "", "", "", "internal", "Control"]),
    ]
    assert (
        field_insert_row_index(register_only, register_index=0, field_index=None) == 1
    )


def test_visible_rows_hides_collapsed_fields() -> None:
    rows = _example_rows()
    infos = build_row_infos(rows)
    collapsed = toggle_register_collapsed(set(), 0)
    visible = visible_row_infos(infos, collapsed)
    assert len(visible) == 3
    assert visible[0].kind == RowKind.REGISTER
    assert visible[0].register_index == 0
    assert all(
        info.register_index != 0 or info.kind == RowKind.REGISTER for info in visible
    )


def test_visible_field_row_index_expands_after_collapse() -> None:
    rows = _example_rows()
    infos = build_row_infos(rows)
    collapsed = toggle_register_collapsed(set(), 0)
    assert visible_field_row_index(infos, collapsed, 0, 1) is None
    expanded = expand_register(collapsed, 0)
    assert visible_field_row_index(infos, expanded, 0, 1) == 2


def test_delete_register_removes_fields() -> None:
    rows = _example_rows()
    updated = delete_register(rows, 0)
    infos = build_row_infos(updated)
    assert len(infos) == 2
    assert infos[0].kind == RowKind.REGISTER
    assert infos[0].register_index == 0
    assert infos[0].row_dict["register"] == "EVENTS"


def test_delete_field_row() -> None:
    rows = _example_rows()
    updated = delete_field_row(rows, 2)
    infos = build_row_infos(updated)
    assert len(infos) == 4
    assert all(info.row_dict.get("field") != "B" for info in infos)


def test_bit_ruler_helpers() -> None:
    lane_left = 8
    lane_width = 320
    assert bit_boundary_x(31, lane_left=lane_left, lane_width=lane_width) == lane_left
    assert (
        bit_boundary_x(0, lane_left=lane_left, lane_width=lane_width) == lane_left + 310
    )
    assert ruler_tick_rise(0) == 8
    assert ruler_tick_rise(1) == 3
    assert RULER_MAJOR_BITS == frozenset({0, 8, 16, 24, 31})


def test_bit_gaps_and_overlap_rejection() -> None:
    fields = [
        Field(name="LOW", msb=3, lsb=0, access="rw", reset=0),
        Field(name="HIGH", msb=31, lsb=16, access="rw", reset=0),
    ]
    gaps = find_bit_gaps(fields)
    assert any(gap.msb == 15 and gap.lsb == 4 for gap in gaps)

    updated, error = try_update_field_bits(fields, 0, msb=17, lsb=0)
    assert updated is None
    assert error is not None


def test_address_map_lists_gap() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="A",
                address=0x00,
                fields=[Field(name="X", msb=0, lsb=0, access="rw", reset=0)],
            ),
            Register(
                name="B",
                address=0x08,
                fields=[Field(name="Y", msb=0, lsb=0, access="rw", reset=0)],
            ),
        ]
    )
    entries = build_address_map(model)
    assert len(entries) == 2
    gaps = find_address_gaps(model)
    assert any(format_address_gap(gap) == "gap 0x4" for gap in gaps)


def test_address_conflicts_mark_overlapping_registers() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="A",
                address=0x00,
                fields=[Field(name="X", msb=0, lsb=0, access="rw", reset=0)],
            ),
            Register(
                name="B",
                address=0x00,
                fields=[Field(name="Y", msb=0, lsb=0, access="rw", reset=0)],
            ),
        ]
    )
    assert find_conflicting_register_indices(model) == {0, 1}
    timeline = build_address_timeline(model)
    assert timeline is not None
    assert timeline.byte_low == 0
    assert all(register.conflict for register in timeline.registers)


def test_visible_register_row_index() -> None:
    rows = _example_rows()
    infos = build_row_infos(rows)
    assert visible_register_row_index(infos, set(), 0) == 0
    assert visible_register_row_index(infos, set(), 1) == 3


def test_address_map_format_helpers() -> None:
    from csr_gen_gui.address_map import (
        AddressMapEntry,
        TimelineRegister,
        format_address_entry,
        find_address_gaps_between,
        register_timeline_label,
    )

    entry = AddressMapEntry(
        register_index=0,
        name="MEM",
        start=0x20,
        end=0x2F,
        hw_access="external",
        slot_count=4,
    )
    assert "0x20-0x2f" in format_address_entry(entry).lower()
    assert "4 slots" in format_address_entry(entry)

    timeline_register = TimelineRegister(
        register_index=0,
        name="MEM",
        start=0x20,
        end=0x2F,
        hw_access="external",
        conflict=False,
    )
    label = register_timeline_label(timeline_register)
    assert "MEM" in label
    assert "0x20" in label

    gaps = find_address_gaps_between(0, 0x10, {0, 0x8})
    assert any(format_address_gap(gap) == "gap 0x4" for gap in gaps)


def _external_device_model() -> RegisterModel:
    return RegisterModel(
        registers=[
            Register(
                name="STATUS",
                address=0x00,
                hw_access="internal",
                fields=[Field(name="flag", msb=0, lsb=0, access="ro", reset=0)],
            ),
            Register(
                name="FIFO",
                address=0x10,
                hw_access="external",
                fields=[
                    Field(name="data", msb=7, lsb=0, access="rw", reset=0),
                    Field(name="level", msb=15, lsb=8, access="ro", reset=0),
                ],
            ),
            Register(
                name="MEM",
                address=0x20,
                address_end=0x2F,
                hw_access="external",
                fields=[
                    Field(name="window", msb=31, lsb=0, access="rw", reset=0),
                ],
            ),
            Register(
                name="ROM",
                address=0x30,
                address_end=0x3F,
                hw_access="external",
                fields=[Field(name="image", msb=31, lsb=0, access="ro", reset=0)],
            ),
            Register(
                name="WBUF",
                address=0x40,
                address_end=0x4F,
                hw_access="external",
                fields=[Field(name="buffer", msb=31, lsb=0, access="wo", reset=0)],
            ),
        ]
    )


def test_timeline_ruler_ticks_external_device_golden() -> None:
    timeline = build_address_timeline(_external_device_model())
    assert timeline is not None

    ticks = timeline_ruler_ticks(timeline)
    assert [(tick.paint_offset, tick.address) for tick in ticks] == [
        (0x00, 0x00),
        (0x10, 0x10),
        (0x20, 0x20),
        (0x30, 0x30),
        (0x40, 0x40),
        (0x50, 0x4F),
    ]
    assert format_ruler_tick_label(ticks[-1]) == "0x4f"


def test_timeline_ruler_ticks_range_end_when_not_abutting() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="MEM",
                address=0x20,
                address_end=0x2F,
                hw_access="external",
                fields=[Field(name="window", msb=31, lsb=0, access="rw", reset=0)],
            ),
            Register(
                name="LATE",
                address=0x40,
                fields=[Field(name="x", msb=0, lsb=0, access="rw", reset=0)],
            ),
        ]
    )
    timeline = build_address_timeline(model)
    assert timeline is not None

    ticks = timeline_ruler_ticks(timeline)
    assert (0x30, 0x2F) in [(tick.paint_offset, tick.address) for tick in ticks]
    assert (0x40, 0x40) in [(tick.paint_offset, tick.address) for tick in ticks]


def test_timeline_ruler_ticks_abutting_ranges_hide_shared_boundary() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="MEM",
                address=0x20,
                address_end=0x2F,
                hw_access="external",
                fields=[Field(name="window", msb=31, lsb=0, access="rw", reset=0)],
            ),
            Register(
                name="ROM",
                address=0x30,
                address_end=0x3F,
                hw_access="external",
                fields=[Field(name="image", msb=31, lsb=0, access="ro", reset=0)],
            ),
        ]
    )
    timeline = build_address_timeline(model)
    assert timeline is not None

    ticks = timeline_ruler_ticks(timeline)
    assert [(tick.paint_offset, tick.address) for tick in ticks] == [
        (0x20, 0x20),
        (0x30, 0x30),
        (0x40, 0x3F),
    ]


def test_table_insert_and_commit_helpers() -> None:
    from csr_gen_gui.table_editing import (
        RowKind,
        commit_table_cell,
        expand_indicator,
        insert_field_row,
        insert_register_row,
        read_row_values,
        register_cell_text,
        strip_register_indicator,
    )

    rows = _example_rows()
    with_register = insert_register_row(rows, 0, name="NEW", address="10")
    assert with_register[0]["register"] == "NEW"
    assert with_register[0]["address"] == "10"

    with_field = insert_field_row(rows, 1, name="X", bits="3:0")
    assert with_field[1]["field"] == "X"
    assert with_field[1]["bits"] == "3:0"

    assert expand_indicator(True) == "[+]"
    assert expand_indicator(False) == "[−]"
    assert register_cell_text("CTRL", collapsed=True).startswith("[+]")
    assert strip_register_indicator("[−] CTRL") == "CTRL"

    row = read_row_values(["[+] CTRL", "0x00", "", "", "", "", "internal", "Control"])
    assert row["register"] == "CTRL"

    updated = commit_table_cell(
        {"address": "10", "reset": "1"},
        1,
        kind=RowKind.REGISTER,
    )
    assert updated["address"] == "0x10"
    updated_reset = commit_table_cell(
        {"address": "", "reset": "1"},
        5,
        kind=RowKind.FIELD,
    )
    assert updated_reset["reset"] == "0x1"


def test_sort_table_rows_orders_registers_and_fields() -> None:
    from csr_gen_gui.table_editing import sort_table_rows, table_rows_need_sort

    rows = [
        table_row_to_dict(["HIGH", "0x10", "", "", "", "", "internal", "High"]),
        table_row_to_dict(["", "", "TOP", "31:16", "rw", "0x0", "", "Top"]),
        table_row_to_dict(["LOW", "0x0", "", "", "", "", "internal", "Low"]),
        table_row_to_dict(["", "", "FLAG", "0", "rw", "0x0", "", "Flag"]),
        table_row_to_dict(["MID", "0x8", "", "", "", "", "internal", "Mid"]),
        table_row_to_dict(["", "", "WIDE", "15:0", "rw", "0x0", "", "Wide"]),
    ]

    assert table_rows_need_sort(rows) is True
    sorted_rows = sort_table_rows(rows)
    assert table_rows_need_sort(sorted_rows) is False

    register_names = [
        row["register"] for row in sorted_rows if row.get("register", "").strip()
    ]
    assert register_names == ["LOW", "MID", "HIGH"]

    low_index = next(
        index for index, row in enumerate(sorted_rows) if row["register"] == "LOW"
    )
    mid_index = next(
        index for index, row in enumerate(sorted_rows) if row["register"] == "MID"
    )
    high_index = next(
        index for index, row in enumerate(sorted_rows) if row["register"] == "HIGH"
    )
    assert sorted_rows[low_index + 1]["field"] == "FLAG"
    assert sorted_rows[mid_index + 1]["field"] == "WIDE"
    assert sorted_rows[high_index + 1]["field"] == "TOP"


def test_table_rows_need_sort_false_for_single_row() -> None:
    from csr_gen_gui.table_editing import table_rows_need_sort

    rows = [table_row_to_dict(["CTRL", "0x0", "", "", "", "", "internal", "Control"])]
    assert table_rows_need_sort(rows) is False
