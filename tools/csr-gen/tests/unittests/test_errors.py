"""Tests for shared CSR error formatting."""

from csr_gen.errors import CsrValidationError, format_error_messages


def test_format_error_messages_empty_list() -> None:
    assert format_error_messages([]) == "CSR specification is invalid."


def test_format_error_messages_single_message() -> None:
    assert format_error_messages(["bad row"]) == "bad row"


def test_format_error_messages_multiple_messages() -> None:
    text = format_error_messages(["first error", "second error"])
    assert "CSR specification errors:" in text
    assert "first error" in text
    assert "second error" in text


def test_csr_validation_error_wraps_messages() -> None:
    error = CsrValidationError(["row 1: invalid"])
    assert str(error) == "row 1: invalid"
