"""Exceptions raised while reading and validating CSR definitions."""


class CsrGenError(ValueError):
    """Base exception for invalid CSR input."""


def format_error_messages(messages: list[str]) -> str:
    """Format one or more validation messages for CLI output."""
    if not messages:
        return "CSR specification is invalid."
    if len(messages) == 1:
        return messages[0]
    lines = "\n".join(f"  - {message}" for message in messages)
    return f"CSR specification errors:\n{lines}"


class CsrValidationError(CsrGenError):
    """Raised when a CSR specification has one or more validation errors."""

    def __init__(self, messages: list[str]) -> None:
        self.messages = list(messages)
        super().__init__(format_error_messages(self.messages))


class ModelValidationError(CsrValidationError):
    """Raised when a register model violates CSR legality rules."""


class MarkdownParseError(CsrGenError):
    """Raised when a Markdown CSR table cannot be parsed."""


class YamlParseError(CsrGenError):
    """Raised when a YAML CSR model cannot be parsed."""


class IpxactParseError(CsrGenError):
    """Raised when an IP-XACT file cannot be parsed."""
