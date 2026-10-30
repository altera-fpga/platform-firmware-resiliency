"""Tests for validation message formatting."""

from __future__ import annotations

import pytest

from csr_gen_gui.validation_display import (
    ValidationSeverity,
    format_validation_html,
    messages_from_errors,
    parse_validation_message,
    validation_error,
    validation_info,
    validation_warning,
)

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


def test_format_validation_html_uses_severity_colors() -> None:
    html = format_validation_html(
        [
            validation_info("No validation errors."),
            validation_warning("Address gap at 0x08."),
            validation_error("CSR table row 1: Register name must not be empty."),
        ]
    )
    assert "color:#22863a" in html
    assert "INFO:" in html
    assert "color:#b8860b" in html
    assert "WARNING:" in html
    assert "color:#c0392b" in html
    assert "ERROR:" in html
    assert "Register name must not be empty." in html


def test_format_validation_html_escapes_markup() -> None:
    html = format_validation_html([validation_error("<script>&")])
    assert "&lt;script&gt;&amp;" in html
    assert "<script>" not in html


def test_messages_from_errors_default_to_error_severity() -> None:
    messages = messages_from_errors(["bad row", "duplicate name"])
    assert len(messages) == 2
    assert all(message.severity is ValidationSeverity.ERROR for message in messages)


def test_parse_validation_message_recognizes_prefix() -> None:
    message = parse_validation_message("WARNING: overlap detected")
    assert message.severity is ValidationSeverity.WARNING
    assert message.text == "overlap detected"


def test_parse_validation_message_strips_leading_whitespace_before_slicing() -> None:
    message = parse_validation_message("  WARNING: overlap detected")
    assert message.severity is ValidationSeverity.WARNING
    assert message.text == "overlap detected"


def test_parse_validation_message_defaults_to_error() -> None:
    message = parse_validation_message("CSR table row 2: bad bits")
    assert message.severity is ValidationSeverity.ERROR
    assert message.text == "CSR table row 2: bad bits"


def test_validation_panel_renders_messages(qapp) -> None:
    from csr_gen_gui.widgets.validation_panel import ValidationPanel

    panel = ValidationPanel()
    panel.set_messages([validation_info("Ready.")])
    assert "INFO:" in panel.toHtml()
    assert "Ready." in panel.toPlainText()
