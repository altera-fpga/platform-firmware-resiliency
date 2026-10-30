"""Tests for CSR identifier validation."""

import pytest

from csr_gen.model import (
    Field,
    FieldDraft,
    RegisterDraft,
    collect_register_draft_errors,
)
from csr_gen.names import csr_identifier_error, is_valid_csr_identifier


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("CTRL", True),
        ("enable", True),
        ("FIELD_1", True),
        ("_RSVD", True),
        ("A", True),
        ("", False),
        ("1BAD", False),
        ("BAD NAME", False),
        ("BAD-NAME", False),
        ("bad.name", False),
    ],
)
def test_is_valid_csr_identifier(name: str, expected: bool) -> None:
    assert is_valid_csr_identifier(name) is expected


def test_collect_register_draft_errors_rejects_invalid_register_name() -> None:
    draft = RegisterDraft(
        row_number=1,
        name="BAD NAME",
        address=0,
        description="",
        fields=[
            FieldDraft(
                row_number=2,
                name="ENABLE",
                msb=0,
                lsb=0,
                access="rw",
                reset=0,
            )
        ],
    )
    errors = collect_register_draft_errors([draft])
    assert any("Register name 'BAD NAME'" in error for error in errors)


def test_collect_register_draft_errors_rejects_invalid_field_name() -> None:
    draft = RegisterDraft(
        row_number=1,
        name="CTRL",
        address=0,
        description="",
        fields=[
            FieldDraft(
                row_number=2,
                name="bad-field",
                msb=0,
                lsb=0,
                access="rw",
                reset=0,
            )
        ],
    )
    errors = collect_register_draft_errors([draft])
    assert any("Field name 'bad-field'" in error for error in errors)


def test_csr_identifier_error_returns_none_for_valid_name() -> None:
    assert csr_identifier_error("CTRL", kind="Register") is None
