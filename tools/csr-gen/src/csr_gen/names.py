"""CSR register and field identifier validation."""

from __future__ import annotations

import re

_CSR_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def is_valid_csr_identifier(name: str) -> bool:
    """Return whether ``name`` is a legal register or field identifier."""
    stripped = name.strip()
    return bool(stripped) and _CSR_IDENTIFIER.fullmatch(stripped) is not None


def csr_identifier_error(name: str, *, kind: str) -> str | None:
    """Return a validation message when ``name`` is not a legal identifier."""
    stripped = name.strip()
    if not stripped:
        return None
    if is_valid_csr_identifier(stripped):
        return None
    return (
        f"{kind} name {stripped!r} must contain only letters, digits, and "
        "underscores, and must not start with a digit."
    )
