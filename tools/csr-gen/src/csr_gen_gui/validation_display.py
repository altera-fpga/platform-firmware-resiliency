"""Format validation messages with INFO/WARNING/ERROR severity prefixes."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "ValidationMessage",
    "ValidationSeverity",
    "format_validation_html",
    "messages_from_errors",
    "parse_validation_message",
    "validation_error",
    "validation_info",
    "validation_warning",
]

_PREFIX_PATTERN = re.compile(r"^(INFO|WARNING|ERROR):\s*", re.IGNORECASE)


class ValidationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


_PREFIX_COLORS = {
    ValidationSeverity.INFO: "#22863a",
    ValidationSeverity.WARNING: "#b8860b",
    ValidationSeverity.ERROR: "#c0392b",
}


@dataclass(frozen=True)
class ValidationMessage:
    severity: ValidationSeverity
    text: str


def validation_info(text: str) -> ValidationMessage:
    return ValidationMessage(ValidationSeverity.INFO, text)


def validation_warning(text: str) -> ValidationMessage:
    return ValidationMessage(ValidationSeverity.WARNING, text)


def validation_error(text: str) -> ValidationMessage:
    return ValidationMessage(ValidationSeverity.ERROR, text)


def parse_validation_message(text: str) -> ValidationMessage:
    """Parse an optional severity prefix from plain text."""
    normalized = text.strip()
    match = _PREFIX_PATTERN.match(normalized)
    if match is None:
        return validation_error(text)
    severity = ValidationSeverity[match.group(1).upper()]
    body = normalized[match.end() :].strip()
    return ValidationMessage(severity, body)


def messages_from_errors(errors: list[str]) -> list[ValidationMessage]:
    """Convert plain error strings into ERROR-severity messages."""
    return [validation_error(error) for error in errors]


def format_validation_html(messages: list[ValidationMessage]) -> str:
    """Render validation messages as colored HTML for a read-only text pane."""
    if not messages:
        return ""
    lines: list[str] = []
    for message in messages:
        color = _PREFIX_COLORS[message.severity]
        prefix = message.severity.value
        escaped = html.escape(message.text)
        lines.append(
            f'<span style="color:{color}; font-weight:600;">{prefix}:</span> '
            f"{escaped}"
        )
    return "<br/>".join(lines)
