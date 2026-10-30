"""Headless bitfield move/resize helpers for the GUI canvas."""

from __future__ import annotations

from dataclasses import dataclass

from csr_gen.literals import format_hex_literal
from csr_gen.model import REGISTER_WIDTH, Field, SUPPORTED_ACCESS

REGISTER_BITS = REGISTER_WIDTH
RULER_MAJOR_BITS = frozenset({0, 8, 16, 24, 31})
RULER_MINOR_TICK_RISE = 3
RULER_MAJOR_TICK_RISE = 8
DEFAULT_FIELD_ACCESS = "rw"
RESERVED_ACCESS = "none"


def is_reserved_field(access: str) -> bool:
    return access.strip().lower() == RESERVED_ACCESS


def format_access_label(access: str) -> str:
    """Return the short access label shown on each field block."""
    return access.strip().lower() or DEFAULT_FIELD_ACCESS


def field_block_colors(access: str, *, selected: bool) -> tuple[str, str]:
    """Return ``(fill_hex, border_hex)`` for one field slice."""
    if is_reserved_field(access):
        if selected:
            return "#c8c8c8", "#666666"
        return "#dedede", "#888888"
    if selected:
        return "#9ec5fe", "#3366aa"
    return "#cfe2ff", "#3366aa"


def format_field_bit_range(msb: int, lsb: int) -> str:
    if msb == lsb:
        return str(msb)
    return f"{msb}:{lsb}"


@dataclass(frozen=True)
class CalloutLabelSpec:
    """One field label to place in the callout band below the lane."""

    field_index: int
    anchor_x: int
    label_width: int


@dataclass(frozen=True)
class CalloutPlacement:
    """Resolved label row and horizontal position for one field."""

    field_index: int
    anchor_x: int
    label_x: int
    label_width: int
    row: int


def layout_callout_labels(
    specs: list[CalloutLabelSpec],
    *,
    lane_left: int,
    lane_right: int,
    label_padding: int = 4,
) -> tuple[list[CalloutPlacement], int]:
    """Pack field labels into horizontal rows below the bitfield lane."""
    if not specs:
        return [], 0

    lane_width = max(1, lane_right - lane_left)
    occupied_rows: list[list[tuple[int, int]]] = []
    placements: list[CalloutPlacement] = []

    for spec in sorted(specs, key=lambda item: item.anchor_x):
        width = max(1, spec.label_width)
        preferred_left = spec.anchor_x - width // 2
        max_left = lane_left + lane_width - width
        label_left = max(lane_left, min(preferred_left, max_left))

        row = 0
        while True:
            while row >= len(occupied_rows):
                occupied_rows.append([])
            if not _interval_overlaps_row(
                label_left,
                label_left + width,
                occupied_rows[row],
                label_padding,
            ):
                occupied_rows[row].append((label_left, label_left + width))
                placements.append(
                    CalloutPlacement(
                        field_index=spec.field_index,
                        anchor_x=spec.anchor_x,
                        label_x=label_left,
                        label_width=width,
                        row=row,
                    )
                )
                break
            row += 1

    return placements, len(occupied_rows)


def _interval_overlaps_row(
    left: int,
    right: int,
    occupied: list[tuple[int, int]],
    padding: int,
) -> bool:
    for other_left, other_right in occupied:
        if left < other_right + padding and right > other_left - padding:
            return True
    return False


def callout_band_height(*, row_count: int, row_height: int, gap: int) -> int:
    if row_count <= 0:
        return 0
    return gap + row_count * row_height


def bit_boundary_x(bit: int, *, lane_left: int, lane_width: int) -> int:
    """Return the canvas X coordinate for the left edge of one bit column."""
    clamped = max(0, min(REGISTER_BITS - 1, bit))
    return lane_left + int((REGISTER_BITS - 1 - clamped) * lane_width / REGISTER_BITS)


def ruler_tick_rise(bit: int) -> int:
    """Return tick height above the lane for one ruler bit index."""
    return RULER_MAJOR_TICK_RISE if bit in RULER_MAJOR_BITS else RULER_MINOR_TICK_RISE


@dataclass(frozen=True)
class BitSlice:
    """One contiguous field slice within a 32-bit register."""

    index: int
    name: str
    msb: int
    lsb: int
    access: str


@dataclass(frozen=True)
class BitGap:
    """Unused bit range within a register."""

    msb: int
    lsb: int


def fields_to_slices(fields: list[Field]) -> list[BitSlice]:
    return [
        BitSlice(
            index=index,
            name=field.name,
            msb=field.msb,
            lsb=field.lsb,
            access=field.access,
        )
        for index, field in enumerate(fields)
    ]


def find_bit_gaps(fields: list[Field]) -> list[BitGap]:
    """Return unused bit ranges from MSB to LSB."""
    occupied = [False] * REGISTER_BITS
    for field in fields:
        for bit in range(field.lsb, field.msb + 1):
            if 0 <= bit < REGISTER_BITS:
                occupied[bit] = True
    gaps: list[BitGap] = []
    bit = REGISTER_BITS - 1
    while bit >= 0:
        if occupied[bit]:
            bit -= 1
            continue
        gap_msb = bit
        while bit >= 0 and not occupied[bit]:
            bit -= 1
        gaps.append(BitGap(msb=gap_msb, lsb=bit + 1))
    return gaps


def slices_overlap(first: BitSlice, second: BitSlice) -> bool:
    if first.index == second.index:
        return False
    return first.lsb <= second.msb and second.lsb <= first.msb


def _validate_slice(msb: int, lsb: int) -> str | None:
    if lsb < 0 or msb < lsb or msb >= REGISTER_BITS:
        return f"Bit range must fit within 0:{REGISTER_BITS - 1}."
    return None


def try_update_field_bits(
    fields: list[Field],
    field_index: int,
    *,
    msb: int,
    lsb: int,
) -> tuple[list[Field] | None, str | None]:
    """Move or resize one field, rejecting overlaps."""
    if field_index < 0 or field_index >= len(fields):
        return None, "Field index out of range."
    error = _validate_slice(msb, lsb)
    if error:
        return None, error

    candidate = BitSlice(
        index=field_index,
        name=fields[field_index].name,
        msb=msb,
        lsb=lsb,
        access=fields[field_index].access,
    )
    for index, field in enumerate(fields):
        if index == field_index:
            continue
        other = BitSlice(
            index=index,
            name=field.name,
            msb=field.msb,
            lsb=field.lsb,
            access=field.access,
        )
        if slices_overlap(candidate, other):
            return None, f"Field {candidate.name} overlaps {other.name}."

    updated = list(fields)
    original = updated[field_index]
    updated[field_index] = Field(
        name=original.name,
        msb=msb,
        lsb=lsb,
        access=original.access,
        reset=original.reset,
        description=original.description,
    )
    return updated, None


def default_field_name(fields: list[Field]) -> str:
    """Return FIELD, FIELD_1, FIELD_2, … avoiding names already in ``fields``."""
    existing = {field.name.strip().upper() for field in fields}
    if "FIELD" not in existing:
        return "FIELD"
    suffix = 1
    while f"FIELD_{suffix}" in existing:
        suffix += 1
    return f"FIELD_{suffix}"


def format_field_reset(field: Field) -> str:
    return format_hex_literal(field.reset)


def bit_in_gap(gaps: list[BitGap], bit: int) -> bool:
    return any(gap.lsb <= bit <= gap.msb for gap in gaps)


def normalize_drag_bits(anchor_bit: int, current_bit: int) -> tuple[int, int]:
    """Return ``(msb, lsb)`` for a drag between two bit indices."""
    msb = max(anchor_bit, current_bit)
    lsb = min(anchor_bit, current_bit)
    return msb, lsb


def try_create_field(
    fields: list[Field],
    *,
    msb: int,
    lsb: int,
    name: str | None = None,
    access: str = DEFAULT_FIELD_ACCESS,
    reset: int = 0,
) -> tuple[list[Field] | None, str | None]:
    """Append a field when its slice is legal and does not overlap."""
    error = _validate_slice(msb, lsb)
    if error:
        return None, error
    normalized_access = access.strip().lower()
    if normalized_access not in SUPPORTED_ACCESS:
        return None, f"Unsupported access: {access!r}."

    field_name = (name or default_field_name(fields)).strip().upper()
    if not field_name:
        return None, "Field name must not be empty."

    candidate = BitSlice(
        index=len(fields),
        name=field_name,
        msb=msb,
        lsb=lsb,
        access=normalized_access,
    )
    for index, field in enumerate(fields):
        other = BitSlice(
            index=index,
            name=field.name,
            msb=field.msb,
            lsb=field.lsb,
            access=field.access,
        )
        if slices_overlap(candidate, other):
            return None, f"New field {field_name} overlaps {other.name}."

    reset_error = _validate_field_reset(msb, lsb, reset)
    if reset_error:
        return None, reset_error

    updated = list(fields)
    updated.append(
        Field(
            name=field_name,
            msb=msb,
            lsb=lsb,
            access=normalized_access,
            reset=reset,
            description=field_name,
        )
    )
    return updated, None


def try_delete_field(
    fields: list[Field],
    field_index: int,
) -> tuple[list[Field] | None, str | None]:
    if field_index < 0 or field_index >= len(fields):
        return None, "Field index out of range."
    return [field for index, field in enumerate(fields) if index != field_index], None


def try_update_field_access(
    fields: list[Field],
    field_index: int,
    access: str,
) -> tuple[list[Field] | None, str | None]:
    if field_index < 0 or field_index >= len(fields):
        return None, "Field index out of range."
    normalized = access.strip().lower()
    if normalized not in SUPPORTED_ACCESS:
        return None, f"Unsupported access: {access!r}."

    updated = list(fields)
    original = updated[field_index]
    updated[field_index] = Field(
        name=original.name,
        msb=original.msb,
        lsb=original.lsb,
        access=normalized,
        reset=original.reset,
        description=original.description,
    )
    return updated, None


def try_update_field_reset(
    fields: list[Field],
    field_index: int,
    reset: int,
) -> tuple[list[Field] | None, str | None]:
    if field_index < 0 or field_index >= len(fields):
        return None, "Field index out of range."
    original = fields[field_index]
    reset_error = _validate_field_reset(original.msb, original.lsb, reset)
    if reset_error:
        return None, reset_error

    updated = list(fields)
    updated[field_index] = Field(
        name=original.name,
        msb=original.msb,
        lsb=original.lsb,
        access=original.access,
        reset=reset,
        description=original.description,
    )
    return updated, None


def _validate_field_reset(msb: int, lsb: int, reset: int) -> str | None:
    if not isinstance(reset, int) or isinstance(reset, bool) or reset < 0:
        return "Reset must be a non-negative integer."
    width = msb - lsb + 1
    if reset >= 1 << width:
        return f"Reset value {reset:#x} does not fit within {width} bits."
    return None
