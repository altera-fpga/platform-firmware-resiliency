import logging

import click
import pytest

from csr_gen import logging as csr_logging


def test_error_raises_nonzero_click_exception(caplog) -> None:
    csr_logging.configure()

    with caplog.at_level(logging.ERROR, logger="csr_gen"):
        with pytest.raises(click.ClickException) as exception:
            csr_logging.error("invalid register definition")

    assert exception.value.exit_code != 0
    assert "invalid register definition" in str(exception.value)


def test_info_logs_without_raising(caplog) -> None:
    csr_logging.configure()

    with caplog.at_level(logging.INFO, logger="csr_gen"):
        csr_logging.info("reading input file")

    assert "reading input file" in caplog.text


def test_warning_logs_without_raising_by_default(caplog) -> None:
    csr_logging.configure()

    with caplog.at_level(logging.WARNING, logger="csr_gen"):
        csr_logging.warning("register has no reset value")

    assert "register has no reset value" in caplog.text


def test_warning_raises_when_configured_as_error(caplog) -> None:
    csr_logging.configure(warnings_as_errors=True)

    try:
        with caplog.at_level(logging.ERROR, logger="csr_gen"):
            with pytest.raises(click.ClickException) as exception:
                csr_logging.warning("register has no reset value")

        assert exception.value.exit_code != 0
        assert "register has no reset value" in str(exception.value)
    finally:
        csr_logging.configure(warnings_as_errors=False)
