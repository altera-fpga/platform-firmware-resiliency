import logging as stdlib_logging

import click

_LOGGER = stdlib_logging.getLogger("csr_gen")
_warnings_as_errors = False


def configure(*, warnings_as_errors: bool = False) -> None:
    global _warnings_as_errors

    _warnings_as_errors = warnings_as_errors
    _LOGGER.setLevel(stdlib_logging.INFO)
    if not _LOGGER.handlers:
        handler = stdlib_logging.StreamHandler()
        handler.setFormatter(stdlib_logging.Formatter("%(levelname)s: %(message)s"))
        _LOGGER.addHandler(handler)


def info(message: str) -> None:
    _LOGGER.info(message)


def warning(message: str) -> None:
    if _warnings_as_errors:
        error(message)

    _LOGGER.warning(message)


def error(message: str) -> None:
    """Abort the CLI with a non-zero exit. Message is shown once via Click."""
    raise click.ClickException(message)
