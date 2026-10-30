"""Unit tests for csr-gen IP-XACT vendor extensions."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from csr_gen.input.ipxact_extensions import (
    CSR_GEN_IPXACT_NS,
    address_end_from_dim,
    append_field_vendor_access,
    append_register_vendor_extensions,
    csrgen_tag,
    parse_field_vendor_access,
    parse_register_vendor_extensions,
    register_dim_metadata,
)
from csr_gen.model import Field, Register


def test_append_register_vendor_extensions_skips_internal_without_range() -> None:
    register = ET.Element("register")
    append_register_vendor_extensions(
        register,
        hw_access="internal",
        address_end=None,
    )
    assert list(register) == []


def test_parse_register_vendor_extensions_without_extensions() -> None:
    register = ET.Element("register")
    hw_access, address_end = parse_register_vendor_extensions(register)
    assert hw_access == "internal"
    assert address_end is None


def test_append_register_vendor_extensions_exports_address_end_only() -> None:
    register = ET.Element("register")
    append_register_vendor_extensions(
        register,
        hw_access="internal",
        address_end=0x2F,
    )
    hw_access, address_end = parse_register_vendor_extensions(register)
    assert hw_access == "internal"
    assert address_end == 0x2F
    assert len(list(register)) == 1


def test_append_and_parse_register_vendor_extensions() -> None:
    register = ET.Element("register")
    append_register_vendor_extensions(
        register,
        hw_access="external",
        address_end=0x2F,
    )
    hw_access, address_end = parse_register_vendor_extensions(register)
    assert hw_access == "external"
    assert address_end == 0x2F


def test_parse_register_vendor_extensions_ignores_foreign_vendor_children() -> None:
    register = ET.Element("register")
    extensions = ET.SubElement(register, "vendorExtensions")
    ET.SubElement(extensions, "foreignTag").text = "ignored"
    hw_access_element = ET.SubElement(extensions, csrgen_tag("hwAccess"))
    hw_access_element.text = "external"
    hw_access, address_end = parse_register_vendor_extensions(register)
    assert hw_access == "external"
    assert address_end is None


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        ("'h2f", 0x2F),
        ("'h2c", 0x2F),  # legacy last-word converted to last-byte
        ("'H2C", 0x2F),
        ("0x2c", 0x2F),
        ("'d44", 0x2F),
        ("'b101100", 0x2F),
        ("44", 0x2F),
    ],
)
def test_parse_register_vendor_extensions_address_end_literals(
    literal: str,
    expected: int,
) -> None:
    register = ET.Element("register")
    extensions = ET.SubElement(register, "vendorExtensions")
    address_end_element = ET.SubElement(extensions, csrgen_tag("addressEnd"))
    address_end_element.text = literal
    _, address_end = parse_register_vendor_extensions(register)
    assert address_end == expected


def test_address_end_from_dim_defaults_increment_to_four() -> None:
    register = ET.Element("register")
    child = ET.SubElement(register, "dim")
    child.text = "4"
    assert (
        address_end_from_dim(
            register,
            address=0x20,
            parse_int=lambda text, _context: int(text),
        )
        == 0x2F
    )


def test_address_end_from_dim_without_dim_returns_none() -> None:
    register = ET.Element("register")
    assert (
        address_end_from_dim(
            register,
            address=0x20,
            parse_int=lambda text, _context: int(text),
        )
        is None
    )


def test_address_end_from_dim_honors_dim_increment() -> None:
    register = ET.Element("register")
    ET.SubElement(register, "dim").text = "4"
    ET.SubElement(register, "dimIncrement").text = "8"
    assert (
        address_end_from_dim(
            register,
            address=0x20,
            parse_int=lambda text, _context: int(text),
        )
        == 0x3B
    )


def test_register_dim_metadata_for_external_range() -> None:
    register = Register(
        name="MEM",
        address=0x20,
        address_end=0x2F,
        hw_access="external",
        fields=[Field(name="WINDOW", msb=31, lsb=0, access="rw", reset=0)],
    )
    assert register_dim_metadata(register) == (4, 4)


def test_register_dim_metadata_for_single_address_register() -> None:
    register = Register(
        name="CTRL",
        address=0,
        fields=[Field(name="A", msb=0, lsb=0, access="rw", reset=0)],
    )
    assert register_dim_metadata(register) == (None, None)


def test_append_and_parse_field_vendor_access() -> None:
    field = ET.Element("field")
    append_field_vendor_access(field, "none")
    assert parse_field_vendor_access(field) == "none"
    field2 = ET.Element("field")
    append_field_vendor_access(field2, "r0w1c")
    assert parse_field_vendor_access(field2) == "r0w1c"
    field3 = ET.Element("field")
    append_field_vendor_access(field3, "rw")
    assert field3.find("vendorExtensions") is None


def test_parse_field_vendor_access_returns_none_without_extensions() -> None:
    field = ET.Element("field")
    assert parse_field_vendor_access(field) is None


def test_parse_field_vendor_access_returns_none_without_csrgen_access() -> None:
    field = ET.Element("field")
    extensions = ET.SubElement(field, "vendorExtensions")
    ET.SubElement(extensions, "access").text = "none"
    assert parse_field_vendor_access(field) is None


def test_parse_field_vendor_access_returns_none_for_blank_access() -> None:
    field = ET.Element("field")
    extensions = ET.SubElement(field, "vendorExtensions")
    access = ET.SubElement(extensions, csrgen_tag("access"))
    access.text = "   "
    assert parse_field_vendor_access(field) is None


def test_address_end_from_dim_ignores_single_element_arrays() -> None:
    register = ET.Element("register")
    child = ET.SubElement(register, "dim")
    child.text = "1"
    assert (
        address_end_from_dim(
            register,
            address=0x20,
            parse_int=lambda text, _context: int(text),
        )
        is None
    )


def test_csrgen_tag_uses_namespace() -> None:
    assert CSR_GEN_IPXACT_NS in csrgen_tag("access")
