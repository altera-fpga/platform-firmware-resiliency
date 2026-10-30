"""Map csr-gen field access keywords to SystemRDL field properties."""

from __future__ import annotations

import re

ACCESS_UDP_NAME = "csr_gen_access"
ADDRESS_END_UDP_NAME = "csr_gen_address_end"

_RDL_KEYWORDS = frozenset(
    {
        "abstract",
        "addrmap",
        "alias",
        "constraint",
        "default",
        "enum",
        "encode",
        "external",
        "field",
        "internal",
        "mem",
        "property",
        "reg",
        "regfile",
        "signal",
        "struct",
    }
)


def rdl_identifier(name: str) -> str:
    """Return a SystemRDL-safe identifier."""
    cleaned = re.sub(r"[^0-9a-zA-Z_]", "_", name.strip())
    if not cleaned:
        raise ValueError("SystemRDL identifier must not be empty.")
    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    if cleaned in _RDL_KEYWORDS:
        cleaned = f"_{cleaned}"
    return cleaned


def rdl_escape_string(value: str) -> str:
    """Escape a string for SystemRDL double-quoted literals."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def field_access_properties(access: str) -> tuple[str, str | None, str | None, str]:
    """Return sw, onread, onwrite, and hw properties for a csr-gen access key."""
    normalized = access.strip().lower()
    mapping: dict[str, tuple[str, str | None, str | None, str]] = {
        "none": ("r", None, None, "r"),
        "ro": ("r", None, None, "r"),
        "rc": ("r", "rclr", None, "r"),
        "rw": ("rw", None, None, "rw"),
        "wo": ("w", None, None, "r"),
        "r0w1c": ("rw", "rclr", "woset", "rw"),
        "rw1s": ("rw", None, "woset", "rw"),
        "rw1c": ("rw", None, "woclr", "rw"),
        "rw0c": ("rw", None, "wzc", "rw"),
    }
    if normalized not in mapping:
        raise ValueError(f"Unsupported field access for SystemRDL export: {access!r}.")
    return mapping[normalized]


def access_from_rdl_properties(
    *,
    csr_gen_access: str | None,
    sw: object,
    onread: object | None,
    onwrite: object | None,
) -> str:
    """Derive a csr-gen access keyword from SystemRDL field properties."""
    if csr_gen_access is not None:
        normalized = str(csr_gen_access).strip().lower()
        field_access_properties(normalized)
        return normalized

    sw_name = _enum_name(sw)
    onread_name = _enum_name(onread)
    onwrite_name = _enum_name(onwrite)

    if sw_name == "r" and onread_name == "rclr":
        return "rc"
    if sw_name == "rw" and onread_name == "rclr" and onwrite_name == "woset":
        return "r0w1c"
    if sw_name == "rw" and onwrite_name == "woset":
        return "rw1s"
    if sw_name == "rw" and onwrite_name == "woclr":
        return "rw1c"
    if sw_name == "rw" and onwrite_name == "wzc":
        return "rw0c"
    if sw_name == "w":
        return "wo"
    if sw_name == "rw":
        return "rw"
    if sw_name == "r":
        return "ro"
    raise ValueError(
        "Unsupported SystemRDL field access combination: "
        f"sw={sw_name!r}, onread={onread_name!r}, onwrite={onwrite_name!r}."
    )


def _enum_name(value: object | None) -> str | None:
    if value is None:
        return None
    name = getattr(value, "name", None)
    if name is not None:
        return str(name)
    text = str(value)
    if "." in text:
        return text.rsplit(".", maxsplit=1)[-1]
    return text
