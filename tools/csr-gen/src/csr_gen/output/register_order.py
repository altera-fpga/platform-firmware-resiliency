"""Canonical register and field ordering for csr-gen serializers."""

from __future__ import annotations

from csr_gen.model import Field, Register, RegisterModel


def sorted_registers(model: RegisterModel) -> list[Register]:
    """Return registers sorted by address (lowest first)."""
    return sorted(model.registers, key=lambda register: register.address)


def sorted_fields(register: Register) -> list[Field]:
    """Return fields sorted by LSB (lowest first), matching C header export order."""
    return sorted(register.fields, key=lambda field: field.lsb)
