"""Serialize CSR register models to IP-XACT component XML (IEEE 1685-2014)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from csr_gen.input.ipxact_extensions import (
    append_field_vendor_access,
    append_register_vendor_extensions,
    register_dim_metadata,
)
from csr_gen.input.ipxact_reader import IPXACT_NAMESPACE
from csr_gen.model import (
    Field,
    Register,
    RegisterModel,
    register_decoder_byte_high,
    register_has_address_range,
)
from csr_gen.output.register_order import sorted_fields, sorted_registers
from csr_gen.output.systemverilog_writer import module_name_from_section

ET.register_namespace("ipxact", IPXACT_NAMESPACE)

EXPORT_ACCESS: dict[str, tuple[str, str | None]] = {
    "none": ("read-only", None),
    "rw": ("read-write", None),
    "ro": ("read-only", None),
    "wo": ("write-only", None),
    "r0w1c": ("read-write", None),
    "rw1c": ("read-write", "oneToClear"),
    "rw1s": ("read-write", "oneToSet"),
    "rw0c": ("read-write", "zeroToClear"),
    "rc": ("read-only", "clear"),
}


def write_ipxact_file(
    path: Path,
    model: RegisterModel,
    *,
    memory_map_name: str,
    component_name: str | None = None,
) -> None:
    """Write an IP-XACT component file for a register model."""
    path.write_text(
        write_ipxact(
            model, memory_map_name=memory_map_name, component_name=component_name
        ),
        encoding="utf-8",
    )


def write_ipxact(
    model: RegisterModel,
    *,
    memory_map_name: str,
    component_name: str | None = None,
) -> str:
    """Render a register model as an IP-XACT component XML document."""
    map_name = memory_map_name.strip()
    component_id = (component_name or module_name_from_section(map_name)).strip()
    root = ET.Element(_tag("component"))
    _append_text(root, "vendor", "csr-gen")
    _append_text(root, "library", "generated")
    _append_text(root, "name", component_id)
    _append_text(root, "version", "0.1")

    memory_maps = ET.SubElement(root, _tag("memoryMaps"))
    memory_map = ET.SubElement(memory_maps, _tag("memoryMap"))
    _append_text(memory_map, "name", component_id)
    if map_name != component_id:
        _append_text(memory_map, "description", map_name)

    address_block = ET.SubElement(memory_map, _tag("addressBlock"))
    _append_text(address_block, "name", component_id)
    _append_text(address_block, "baseAddress", "'h0")
    high_byte = register_decoder_byte_high(model)
    span = max(4, high_byte + 4)
    _append_text(address_block, "range", f"'h{span:x}")
    _append_text(address_block, "width", "32")
    _append_text(address_block, "usage", "register")

    for register in sorted_registers(model):
        _append_register(address_block, register)

    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{body}\n'


def _append_register(parent: ET.Element, register: Register) -> None:
    element = ET.SubElement(parent, _tag("register"))
    _append_text(element, "name", register.name)
    if register.description:
        _append_text(element, "description", register.description)
    _append_text(element, "addressOffset", f"'h{register.address:x}")
    dim, dim_increment = register_dim_metadata(register)
    if dim is not None:
        _append_text(element, "dim", str(dim))
        _append_text(element, "dimIncrement", str(dim_increment))
    _append_text(element, "size", "32")
    _append_text(element, "access", "read-write")
    append_register_vendor_extensions(
        element,
        hw_access=register.hw_access,
        address_end=(
            register.address_end if register_has_address_range(register) else None
        ),
    )
    for field in sorted_fields(register):
        _append_field(element, field)


def _append_field(parent: ET.Element, field: Field) -> None:
    element = ET.SubElement(parent, _tag("field"))
    _append_text(element, "name", field.name)
    if field.description:
        _append_text(element, "description", field.description)
    _append_text(element, "bitOffset", str(field.lsb))
    _append_text(element, "bitWidth", str(field.msb - field.lsb + 1))
    access, modified = _export_access(field.access)
    _append_text(element, "access", access)
    if modified is not None:
        _append_text(element, "modifiedWriteValue", modified)
    append_field_vendor_access(element, field.access)
    resets = ET.SubElement(element, _tag("resets"))
    reset = ET.SubElement(resets, _tag("reset"))
    _append_text(reset, "value", f"'h{field.reset:x}")


def _export_access(access: str) -> tuple[str, str | None]:
    mapped = EXPORT_ACCESS.get(access)
    if mapped is None:
        return "read-write", None
    return mapped


def _append_text(parent: ET.Element, local_name: str, text: str) -> ET.Element:
    child = ET.SubElement(parent, _tag(local_name))
    child.text = text
    return child


def _tag(local_name: str) -> str:
    return f"{{{IPXACT_NAMESPACE}}}{local_name}"
