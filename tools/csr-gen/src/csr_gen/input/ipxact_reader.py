"""Read CSR register models from IP-XACT component XML (IEEE 1685-2014 / SPIRIT 2009)."""

from __future__ import annotations

from dataclasses import dataclass
import xml.etree.ElementTree as ET
from pathlib import Path

from csr_gen import logging
from csr_gen.input.ipxact_extensions import (
    address_end_from_dim,
    parse_field_vendor_access,
    parse_register_vendor_extensions,
)
from csr_gen.errors import CsrValidationError, IpxactParseError
from csr_gen.model import (
    FieldDraft,
    RegisterDraft,
    RegisterModel,
    collect_register_draft_errors,
    drafts_to_model,
    row_error,
)

IPXACT_NAMESPACE = "http://www.accellera.org/XMLSchema/IPXACT/1685-2014"
SUPPORTED_ROOT_LOCAL_NAME = "component"

FIELD_CHILDREN_HANDLED = frozenset(
    {
        "name",
        "description",
        "bitOffset",
        "bitWidth",
        "resets",
        "reset",
        "value",
        "access",
        "displayName",
        "volatile",
        "modifiedWriteValue",
        "readAction",
        "enumeratedValues",
        "enumeratedValue",
        "vendorExtensions",
    }
)
REGISTER_CHILDREN_HANDLED = frozenset(
    {
        "name",
        "description",
        "addressOffset",
        "size",
        "access",
        "field",
        "displayName",
        "volatile",
        "dim",
        "dimIncrement",
        "vendorExtensions",
    }
)
ADDRESS_BLOCK_CHILDREN_HANDLED = frozenset(
    {
        "name",
        "description",
        "baseAddress",
        "range",
        "width",
        "usage",
        "register",
    }
)
MEMORY_MAP_CHILDREN_HANDLED = frozenset(
    {"name", "description", "addressBlock", "register"}
)

ACCESS_MAP = {
    "read-write": "rw",
    "read-only": "ro",
    "write-only": "wo",
}
MODIFIED_WRITE_ACCESS_MAP = {
    "oneToClear": "rw1c",
    "oneToSet": "rw1s",
    "zeroToClear": "rw0c",
    "clear": "rc",
}


@dataclass
class IpxactRegisterSpec:
    """A register model parsed from an IP-XACT memory map."""

    model: RegisterModel
    section_heading: str
    memory_map_name: str
    heading_level: int = 2


class _WarnTracker:
    """Emit one warning per unknown element type."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def unknown_child(self, parent: str, element: ET.Element) -> None:
        tag = _local_name(element)
        key = f"{parent}.{tag}"
        if key in self._seen:
            return
        self._seen.add(key)
        logging.warning(
            f"IP-XACT: ignoring unsupported element <{tag}> under <{parent}>."
        )


def load_ipxact_file(
    path: Path,
    *,
    address_block_name: str | None = None,
) -> IpxactRegisterSpec:
    """Read and validate CSR registers from an IP-XACT component file."""
    return load_ipxact(
        path.read_text(encoding="utf-8"),
        path.name,
        address_block_name=address_block_name,
    )


def load_ipxact(
    xml_text: str,
    source: str = "<string>",
    *,
    address_block_name: str | None = None,
) -> IpxactRegisterSpec:
    """Read and validate CSR registers from IP-XACT XML text."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as error:
        raise IpxactParseError(
            f"IP-XACT file {source!r} is not well-formed XML: {error}"
        ) from error

    if _local_name(root) != SUPPORTED_ROOT_LOCAL_NAME:
        raise IpxactParseError(
            f"IP-XACT file {source!r} must have root element <component>."
        )

    vendor = (_child_text(root, "vendor") or "").strip()

    tracker = _WarnTracker()
    _warn_component_extras(root, tracker)

    memory_maps = _children(root, "memoryMaps")
    if memory_maps is None:
        raise IpxactParseError(f"IP-XACT file {source!r} has no <memoryMaps> element.")
    map_elements = _children(memory_maps, "memoryMap", all=True)
    if len(map_elements) == 0:
        raise IpxactParseError(f"IP-XACT file {source!r} has no <memoryMap> element.")
    if len(map_elements) > 1:
        names = ", ".join(
            _child_text(element, "name") or "<unnamed>" for element in map_elements
        )
        raise IpxactParseError(
            f"IP-XACT file {source!r} must contain exactly one <memoryMap>; "
            f"found: {names}."
        )

    memory_map = map_elements[0]
    memory_map_name = _child_text(memory_map, "name")
    if not memory_map_name:
        raise IpxactParseError(f"IP-XACT file {source!r} memoryMap is missing <name>.")
    memory_map_description = _child_text(memory_map, "description")
    if memory_map_description and vendor == "csr-gen":
        section_heading = memory_map_description
    else:
        section_heading = memory_map_name

    _warn_children(memory_map, "memoryMap", MEMORY_MAP_CHILDREN_HANDLED, tracker)

    map_registers = _children(memory_map, "register", all=True)
    if map_registers:
        raise IpxactParseError(
            f"IP-XACT file {source!r} has <register> elements directly under "
            f"<memoryMap>; registers must be inside <addressBlock>."
        )

    blocks = _select_address_blocks(
        memory_map, source=source, address_block_name=address_block_name
    )
    drafts = _collect_register_drafts(blocks, tracker)
    errors = collect_register_draft_errors(drafts)
    if errors:
        raise CsrValidationError(errors)

    return IpxactRegisterSpec(
        model=drafts_to_model(drafts),
        section_heading=section_heading,
        memory_map_name=memory_map_name,
    )


def list_ipxact_address_block_names(
    xml_text: str,
    source: str = "<string>",
) -> list[str]:
    """Return ``addressBlock`` names from the sole memory map in an IP-XACT file."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as error:
        raise IpxactParseError(
            f"IP-XACT file {source!r} is not well-formed XML: {error}"
        ) from error

    if _local_name(root) != SUPPORTED_ROOT_LOCAL_NAME:
        raise IpxactParseError(
            f"IP-XACT file {source!r} must have root element <component>."
        )

    memory_maps = _children(root, "memoryMaps")
    if memory_maps is None:
        raise IpxactParseError(f"IP-XACT file {source!r} has no <memoryMaps> element.")
    map_elements = _children(memory_maps, "memoryMap", all=True)
    if len(map_elements) != 1:
        raise IpxactParseError(
            f"IP-XACT file {source!r} must contain exactly one <memoryMap>."
        )

    blocks = _children(map_elements[0], "addressBlock", all=True)
    if not blocks:
        raise IpxactParseError(
            f"IP-XACT file {source!r} has no <addressBlock> elements."
        )
    return [_child_text(block, "name") or "<unnamed>" for block in blocks]


def list_ipxact_address_block_names_file(path: Path) -> list[str]:
    """Return ``addressBlock`` names from an IP-XACT component file."""
    return list_ipxact_address_block_names(
        path.read_text(encoding="utf-8"),
        path.name,
    )


def _warn_component_extras(root: ET.Element, tracker: _WarnTracker) -> None:
    for child in root:
        tag = _local_name(child)
        if tag == "memoryMaps":
            continue
        tracker.unknown_child("component", child)


def _select_address_blocks(
    memory_map: ET.Element,
    *,
    source: str,
    address_block_name: str | None,
) -> list[ET.Element]:
    blocks = _children(memory_map, "addressBlock", all=True)
    if not blocks:
        raise IpxactParseError(
            f"IP-XACT file {source!r} has no <addressBlock> elements."
        )

    if len(blocks) > 1 and address_block_name is None:
        names = ", ".join(_child_text(block, "name") or "<unnamed>" for block in blocks)
        raise IpxactParseError(
            f"IP-XACT file {source!r} has {len(blocks)} <addressBlock> elements; "
            f"use --ipxact-address-block to select one. Blocks: {names}."
        )

    if address_block_name is not None:
        matched = [
            block
            for block in blocks
            if _child_text(block, "name") == address_block_name
        ]
        if not matched:
            raise IpxactParseError(
                f"IP-XACT file {source!r} has no <addressBlock> named "
                f"{address_block_name!r}."
            )
        return matched

    return blocks


def _collect_register_drafts(
    blocks: list[ET.Element], tracker: _WarnTracker
) -> list[RegisterDraft]:
    drafts: list[RegisterDraft] = []
    for block in blocks:
        _warn_children(block, "addressBlock", ADDRESS_BLOCK_CHILDREN_HANDLED, tracker)
        drafts.extend(_registers_from_block(block, tracker))
    drafts.sort(key=lambda draft: (draft.address, draft.row_number))
    return drafts


def _registers_from_block(
    block: ET.Element, tracker: _WarnTracker
) -> list[RegisterDraft]:
    drafts: list[RegisterDraft] = []
    for register in _children(block, "register", all=True):
        drafts.extend(_register_draft_from_element(register, tracker))
    return drafts


def _register_draft_from_element(
    register: ET.Element, tracker: _WarnTracker
) -> list[RegisterDraft]:
    _warn_children(register, "register", REGISTER_CHILDREN_HANDLED, tracker)
    name = _child_text(register, "name")
    if not name:
        raise IpxactParseError("IP-XACT register is missing <name>.")

    address_text = _child_text(register, "addressOffset")
    if address_text is None:
        raise IpxactParseError(f"IP-XACT register {name!r} is missing <addressOffset>.")

    row_number = 1
    address = _parse_int(address_text, f"register {name} addressOffset")
    register_access = _child_text(register, "access")
    description = _normalize_description(_child_text(register, "description"))

    fields = _children(register, "field", all=True)
    if not fields:
        logging.warning(
            f"IP-XACT: register {name!r} has no <field> elements; skipping."
        )
        return []

    field_drafts: list[FieldDraft] = []
    for index, field in enumerate(fields):
        field_drafts.append(
            _parse_field_draft(
                field,
                row_number=index + 1,
                register_name=name,
                register_access=register_access,
                tracker=tracker,
            )
        )

    register_description = description or field_drafts[0].name
    hw_access, address_end = parse_register_vendor_extensions(register)
    if address_end is None:
        address_end = address_end_from_dim(
            register,
            address=address,
            parse_int=_parse_int,
        )
    return [
        RegisterDraft(
            row_number=row_number,
            name=name,
            address=address,
            description=register_description,
            fields=field_drafts,
            hw_access=hw_access,
            address_end=address_end,
        )
    ]


def _parse_field_draft(
    field: ET.Element,
    *,
    row_number: int,
    register_name: str,
    register_access: str | None,
    tracker: _WarnTracker,
) -> FieldDraft:
    _warn_children(field, "field", FIELD_CHILDREN_HANDLED, tracker)
    name = _child_text(field, "name")
    if not name:
        raise IpxactParseError(
            f"IP-XACT register {register_name!r} has a field without <name>."
        )

    bit_offset_text = _child_text(field, "bitOffset")
    bit_width_text = _child_text(field, "bitWidth")
    if bit_offset_text is None or bit_width_text is None:
        raise IpxactParseError(
            f"IP-XACT register {register_name!r} field {name!r} requires "
            "<bitOffset> and <bitWidth>."
        )

    bit_offset = _parse_int(bit_offset_text, f"{register_name}.{name} bitOffset")
    bit_width = _parse_int(bit_width_text, f"{register_name}.{name} bitWidth")
    if bit_width <= 0:
        raise IpxactParseError(
            row_error(row_number, f"Field {name} bitWidth must be positive.")
        )
    msb = bit_offset + bit_width - 1
    lsb = bit_offset

    access = _map_access(
        field_access=_child_text(field, "access") or register_access,
        modified_write=_child_text(field, "modifiedWriteValue"),
        read_action=_child_text(field, "readAction"),
        context=f"{register_name}.{name}",
    )
    vendor_access = parse_field_vendor_access(field)
    if vendor_access is not None:
        access = vendor_access
    reset = _parse_reset(field, register_name=register_name, field_name=name)
    description = _normalize_description(_child_text(field, "description")) or name

    return FieldDraft(
        row_number=row_number,
        name=name,
        msb=msb,
        lsb=lsb,
        access=access,
        reset=reset,
        description=description,
    )


def _map_access(
    *,
    field_access: str | None,
    modified_write: str | None,
    read_action: str | None,
    context: str,
) -> str:
    if not field_access:
        raise IpxactParseError(
            f"IP-XACT field {context} has no <access> and no register default."
        )

    normalized = field_access.strip().lower()
    if normalized not in ACCESS_MAP:
        raise IpxactParseError(
            f"IP-XACT field {context} has unsupported access {field_access!r}."
        )

    access = ACCESS_MAP[normalized]
    if modified_write:
        modified = modified_write.strip()
        mapped = MODIFIED_WRITE_ACCESS_MAP.get(modified)
        if mapped is None:
            logging.warning(
                f"IP-XACT: unsupported modifiedWriteValue {modified_write!r} "
                f"on {context}; using {access!r}."
            )
        elif access == "rw":
            access = mapped
        else:
            logging.warning(
                f"IP-XACT: modifiedWriteValue on {context} ignored "
                f"for access {field_access!r}."
            )
    if read_action and read_action.strip() not in {"", "clear"}:
        logging.warning(
            f"IP-XACT: unsupported readAction {read_action!r} on {context}; ignored."
        )
    return access


def _parse_reset(field: ET.Element, *, register_name: str, field_name: str) -> int:
    resets = _children(field, "resets")
    if resets is None:
        return 0
    for reset in resets:
        if _local_name(reset) == "reset":
            value = _child_text(reset, "value")
            if value is not None:
                return _parse_int(value, f"{register_name}.{field_name} reset value")
    return 0


def _parse_int(value: str, context: str) -> int:
    text = value.strip()
    try:
        if text.startswith("'h") or text.startswith("'H"):
            return int(text[2:], 16)
        if text.lower().startswith("0x"):
            return int(text, 0)
        if text.startswith("'d") or text.startswith("'D"):
            return int(text[2:], 10)
        if text.startswith("'b") or text.startswith("'B"):
            return int(text[2:], 2)
        return int(text, 0)
    except ValueError as error:
        raise IpxactParseError(
            f"IP-XACT {context} must be an integer; got {value!r}."
        ) from error


def _normalize_description(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.split())


def _warn_children(
    parent: ET.Element,
    parent_name: str,
    handled: frozenset[str],
    tracker: _WarnTracker,
) -> None:
    for child in parent:
        tag = _local_name(child)
        if tag not in handled:
            tracker.unknown_child(parent_name, child)


def _children(
    parent: ET.Element, local_name: str, *, all: bool = False
) -> list[ET.Element] | ET.Element | None:
    matches = [child for child in parent if _local_name(child) == local_name]
    if not matches:
        return [] if all else None
    if all:
        return matches
    if len(matches) > 1:
        parent_tag = _local_name(parent)
        raise IpxactParseError(
            f"IP-XACT element <{parent_tag}> has multiple <{local_name}> children."
        )
    return matches[0]


def _child_text(parent: ET.Element, local_name: str) -> str | None:
    child = _children(parent, local_name)
    if child is None:
        return None
    return (child.text or "").strip() or None


def _local_name(element: ET.Element) -> str:
    return element.tag.rpartition("}")[-1]
