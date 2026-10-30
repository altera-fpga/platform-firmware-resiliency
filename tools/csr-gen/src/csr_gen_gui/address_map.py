"""Headless address map summaries for the GUI."""

from __future__ import annotations

from dataclasses import dataclass

from csr_gen.model import (
    REGISTER_BYTES,
    RegisterModel,
    register_address_end,
    register_occupied_offsets,
    register_slot_count,
)


@dataclass(frozen=True)
class AddressMapEntry:
    """One row in the address map view."""

    register_index: int
    name: str
    start: int
    end: int
    hw_access: str
    slot_count: int


@dataclass(frozen=True)
class AddressGap:
    """Unused byte offset span between registers."""

    start: int
    end: int


@dataclass(frozen=True)
class TimelineRegister:
    """One register block in the horizontal address timeline."""

    register_index: int
    name: str
    start: int
    end: int
    hw_access: str
    conflict: bool


@dataclass(frozen=True)
class AddressTimeline:
    """Layout data for the vertical address map widget (0x0 at the bottom)."""

    byte_low: int
    byte_high: int
    registers: list[TimelineRegister]
    gaps: list[AddressGap]


@dataclass(frozen=True)
class RulerTick:
    """One y-axis ruler mark on the address map timeline."""

    paint_offset: int
    address: int


def build_address_map(model: RegisterModel) -> list[AddressMapEntry]:
    entries: list[AddressMapEntry] = []
    for index, register in enumerate(model.registers):
        end = register_address_end(register)
        slot_count = register_slot_count(register)
        entries.append(
            AddressMapEntry(
                register_index=index,
                name=register.name,
                start=register.address,
                end=end,
                hw_access=register.hw_access,
                slot_count=slot_count,
            )
        )
    return sorted(entries, key=lambda entry: entry.start)


def find_address_gaps(model: RegisterModel) -> list[AddressGap]:
    if not model.registers:
        return []
    occupied: set[int] = set()
    for register in model.registers:
        end = register_address_end(register)
        for offset in range(register.address, end + 1, 4):
            occupied.add(offset)

    if not occupied:
        return []

    low = min(occupied)
    high = max(occupied)
    return find_address_gaps_between(low, high, occupied)


def find_address_gaps_between(
    low: int,
    high: int,
    occupied: set[int],
) -> list[AddressGap]:
    """Return unused 4-byte slots between ``low`` and ``high`` inclusive."""
    gaps: list[AddressGap] = []
    offset = low
    while offset <= high:
        if offset in occupied:
            offset += 4
            continue
        gap_start = offset
        while offset <= high and offset not in occupied:
            offset += 4
        gaps.append(AddressGap(start=gap_start, end=offset - 4))
    return gaps


def find_conflicting_register_indices(model: RegisterModel) -> set[int]:
    """Return register indices that claim the same 4-byte offset."""
    offset_to_indices: dict[int, list[int]] = {}
    for index, register in enumerate(model.registers):
        for offset in register_occupied_offsets(register):
            offset_to_indices.setdefault(offset, []).append(index)

    conflicting: set[int] = set()
    for indices in offset_to_indices.values():
        if len(indices) > 1:
            conflicting.update(indices)
    return conflicting


def build_address_timeline(model: RegisterModel) -> AddressTimeline | None:
    """Build vertical timeline data for the active bank (0x0 at the bottom)."""
    if not model.registers:
        return None

    conflicts = find_conflicting_register_indices(model)
    occupied: set[int] = set()
    for register in model.registers:
        occupied.update(register_occupied_offsets(register))

    byte_low = 0
    byte_high = max(occupied)
    registers = [
        TimelineRegister(
            register_index=entry.register_index,
            name=entry.name,
            start=entry.start,
            end=entry.end,
            hw_access=entry.hw_access,
            conflict=entry.register_index in conflicts,
        )
        for entry in build_address_map(model)
    ]
    return AddressTimeline(
        byte_low=byte_low,
        byte_high=byte_high,
        registers=registers,
        gaps=find_address_gaps_between(byte_low, byte_high, occupied),
    )


def format_address_entry(entry: AddressMapEntry) -> str:
    if entry.start == entry.end:
        address = f"{entry.start:#x}"
    else:
        address = f"{entry.start:#x}-{entry.end:#x}"
    slots = f"{entry.slot_count} slot" + ("s" if entry.slot_count != 1 else "")
    return f"{entry.name:16} {address:16} {entry.hw_access:8} ({slots})"


def format_address_gap(gap: AddressGap) -> str:
    if gap.start == gap.end:
        return f"gap {gap.start:#x}"
    return f"gap {gap.start:#x}-{gap.end:#x}"


def register_timeline_label(register: TimelineRegister) -> str:
    """Return a short label for one timeline register block."""
    if register.start == register.end:
        address = f"{register.start:#x}"
    else:
        address = f"{register.start:#x}-{register.end:#x}"
    return f"{register.name}\n{address}"


def timeline_ruler_ticks(timeline: AddressTimeline) -> list[RulerTick]:
    """Return semantic y-axis ruler ticks for the address map timeline."""
    ticks: list[RulerTick] = []
    map_top = timeline.byte_high + 1
    registers = timeline.registers

    for index, register in enumerate(registers):
        ticks.append(RulerTick(paint_offset=register.start, address=register.start))
        if register.start == register.end:
            continue

        top_exclusive = register.end + 1
        abuts_next = (
            index + 1 < len(registers) and registers[index + 1].start == top_exclusive
        )
        at_map_top = top_exclusive == map_top
        if not abuts_next or at_map_top:
            ticks.append(RulerTick(paint_offset=top_exclusive, address=register.end))

    return sorted(ticks, key=lambda tick: tick.paint_offset)


def format_ruler_tick_label(tick: RulerTick) -> str:
    """Return the text shown beside one ruler tick mark."""
    return f"{tick.address:#x}"
