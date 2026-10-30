"""csr-gen vendor extension helpers for IP-XACT import and export."""

from __future__ import annotations

import xml.etree.ElementTree as ET

CSR_GEN_IPXACT_NS = "http://csr-gen.dev/ipxact/1.0"
CSR_GEN_PREFIX = "csrgen"

ET.register_namespace(CSR_GEN_PREFIX, CSR_GEN_IPXACT_NS)


def csrgen_tag(local_name: str) -> str:
    return f"{{{CSR_GEN_IPXACT_NS}}}{local_name}"


def append_register_vendor_extensions(
    parent: ET.Element,
    *,
    hw_access: str,
    address_end: int | None,
) -> None:
    """Append csr-gen register metadata under ``vendorExtensions``."""
    needs_extensions = hw_access != "internal" or address_end is not None
    if not needs_extensions:
        return
    extensions = ET.SubElement(parent, _ipxact_tag("vendorExtensions"))
    if hw_access != "internal":
        element = ET.SubElement(extensions, csrgen_tag("hwAccess"))
        element.text = hw_access
    if address_end is not None:
        element = ET.SubElement(extensions, csrgen_tag("addressEnd"))
        element.text = f"'h{address_end:x}"


def append_field_vendor_access(parent: ET.Element, access: str) -> None:
    """Preserve csr-gen access keywords that IP-XACT does not encode natively."""
    if access not in {"none", "r0w1c"}:
        return
    extensions = ET.SubElement(parent, _ipxact_tag("vendorExtensions"))
    element = ET.SubElement(extensions, csrgen_tag("access"))
    element.text = access


def parse_register_vendor_extensions(register: ET.Element) -> tuple[str, int | None]:
    """Return ``(hw_access, address_end)`` from csr-gen register extensions."""
    extensions = _child(register, "vendorExtensions")
    if extensions is None:
        return "internal", None

    hw_access = "internal"
    address_end: int | None = None
    for child in extensions:
        local = _local_name(child)
        if not _is_csrgen_element(child):
            continue
        if local == "hwAccess":
            hw_access = (child.text or "internal").strip().lower()
        elif local == "addressEnd":
            address_end = _parse_int(child.text or "", "addressEnd")
    # Legacy addressEnd stored the last word address (4-byte aligned).
    # Inclusive last-byte ends are always 3 mod 4; convert aligned legacy values.
    if address_end is not None and address_end % 4 == 0:
        address_end += 3
    return hw_access, address_end


def parse_field_vendor_access(field: ET.Element) -> str | None:
    """Return a csr-gen access override from field ``vendorExtensions``."""
    extensions = _child(field, "vendorExtensions")
    if extensions is None:
        return None
    for child in extensions:
        if _is_csrgen_element(child) and _local_name(child) == "access":
            return (child.text or "").strip().lower() or None
    return None


def address_end_from_dim(
    register: ET.Element,
    *,
    address: int,
    parse_int,
) -> int | None:
    """Compute inclusive ``address_end`` from IP-XACT ``dim`` metadata."""
    dim_text = _child_text(register, "dim")
    if dim_text is None:
        return None
    dim = parse_int(dim_text, "register dim")
    if dim <= 1:
        return None
    increment_text = _child_text(register, "dimIncrement")
    increment = (
        parse_int(increment_text, "register dimIncrement") if increment_text else 4
    )
    # Last byte of the final 32-bit array element.
    return address + (dim - 1) * increment + 3


def register_dim_metadata(register) -> tuple[int | None, int | None]:
    """Return ``(dim, dimIncrement)`` for a ranged csr-gen register."""
    from csr_gen.model import register_has_address_range, register_slot_count

    if not register_has_address_range(register):
        return None, None
    slot_count = register_slot_count(register)
    return slot_count, 4


def _ipxact_tag(local_name: str) -> str:
    from csr_gen.input.ipxact_reader import IPXACT_NAMESPACE

    return f"{{{IPXACT_NAMESPACE}}}{local_name}"


def _is_csrgen_element(element: ET.Element) -> bool:
    if "}" not in element.tag:
        return False
    namespace, _, _local = element.tag.partition("}")
    return namespace.lstrip("{") == CSR_GEN_IPXACT_NS


def _child(parent: ET.Element, local_name: str) -> ET.Element | None:
    for child in parent:
        if _local_name(child) == local_name:
            return child
    return None


def _child_text(parent: ET.Element, local_name: str) -> str | None:
    child = _child(parent, local_name)
    if child is None:
        return None
    return (child.text or "").strip() or None


def _local_name(element: ET.Element) -> str:
    return element.tag.rpartition("}")[-1]


def _parse_int(value: str, context: str) -> int:
    text = value.strip()
    if text.startswith("'h") or text.startswith("'H"):
        return int(text[2:], 16)
    if text.lower().startswith("0x"):
        return int(text, 0)
    if text.startswith("'d") or text.startswith("'D"):
        return int(text[2:], 10)
    if text.startswith("'b") or text.startswith("'B"):
        return int(text[2:], 2)
    return int(text, 0)
