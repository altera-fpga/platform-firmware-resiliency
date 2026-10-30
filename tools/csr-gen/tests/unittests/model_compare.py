"""Shared helpers for comparing CSR register models in unit tests."""

from csr_gen.model import Field, Register, RegisterModel


def models_equal(left: RegisterModel, right: RegisterModel) -> bool:
    """Return whether two register models are identical."""
    if len(left.registers) != len(right.registers):
        return False
    for left_register, right_register in zip(left.registers, right.registers):
        if not registers_equal(left_register, right_register):
            return False
    return True


def registers_equal(left: Register, right: Register) -> bool:
    """Return whether two registers are identical."""
    if (
        left.name != right.name
        or left.address != right.address
        or left.address_end != right.address_end
        or left.hw_access != right.hw_access
        or left.description != right.description
        or len(left.fields) != len(right.fields)
    ):
        return False
    return all(
        fields_equal(left_field, right_field)
        for left_field, right_field in zip(left.fields, right.fields)
    )


def fields_equal(left: Field, right: Field) -> bool:
    """Return whether two fields are identical."""
    return (
        left.name == right.name
        and left.msb == right.msb
        and left.lsb == right.lsb
        and left.access == right.access
        and left.reset == right.reset
        and left.description == right.description
    )


def assert_models_equal(left: RegisterModel, right: RegisterModel) -> None:
    """Assert that two register models are identical."""
    assert models_equal(left, right)
