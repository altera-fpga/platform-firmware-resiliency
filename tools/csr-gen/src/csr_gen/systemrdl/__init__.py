"""SystemRDL access mapping and shared helpers."""

from csr_gen.systemrdl.access import (
    ACCESS_UDP_NAME,
    ADDRESS_END_UDP_NAME,
    access_from_rdl_properties,
    field_access_properties,
    rdl_escape_string,
    rdl_identifier,
)

__all__ = [
    "ACCESS_UDP_NAME",
    "ADDRESS_END_UDP_NAME",
    "access_from_rdl_properties",
    "field_access_properties",
    "rdl_escape_string",
    "rdl_identifier",
]
