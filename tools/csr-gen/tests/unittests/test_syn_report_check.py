"""Unit tests for Quartus synthesis report checking."""

from pathlib import Path

import pytest

from tests.end2end.commercial_eda.quartus_sv_compile.syn_report_check import (
    SynReportError,
    SynReportSummary,
    check_syn_report,
    load_ignored_message_prefixes,
    parse_syn_report,
)

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "quartus_syn_reports"
_AGILEX_IGNORE = _FIXTURE_DIR / "agilex_harness_ignored.txt"


def test_load_ignored_message_prefixes_skips_comments_and_blanks() -> None:
    path = _FIXTURE_DIR / "nested_one_ignored.txt"
    assert load_ignored_message_prefixes(path) == (
        'Warning (13410): Pin "s_axi_awvalid" is stuck at GND',
    )


def test_parse_syn_report_clean_legacy() -> None:
    summary = parse_syn_report(_FIXTURE_DIR / "clean.syn.rpt")
    assert summary == SynReportSummary(0, 0, 0, 0, 0)
    assert summary.report_lines() == (
        "Warnings: 0 (0 ignored)",
        "Critical warnings: 0 (0 ignored)",
        "Errors: 0",
    )


def test_parse_syn_report_messages_with_ignore_prefixes() -> None:
    summary = parse_syn_report(
        _FIXTURE_DIR / "table_with_allowlisted.rpt",
        ignore_file=_AGILEX_IGNORE,
    )
    assert summary.warnings_total == 1
    assert summary.warnings_ignored == 1
    assert summary.warnings_effective == 0
    assert summary.critical_total == 1
    assert summary.critical_ignored == 1
    assert summary.critical_effective == 0
    assert summary.errors == 0


def test_parse_syn_report_prefix_ignore_on_indented_line() -> None:
    summary = parse_syn_report(
        _FIXTURE_DIR / "messages_stuck_at_prefix.rpt",
        ignore_file=_FIXTURE_DIR / "stuck_at_bresp_ignored.txt",
    )
    assert summary.warnings_total == 1
    assert summary.warnings_ignored == 1
    assert summary.warnings_effective == 0


def test_parse_syn_report_messages_nested_warnings() -> None:
    summary = parse_syn_report(_FIXTURE_DIR / "messages_nested_warnings.rpt")
    assert summary.warnings_total == 3
    assert summary.warnings_ignored == 0
    assert summary.errors == 0


def test_parse_syn_report_nested_warnings_partial_ignore() -> None:
    summary = parse_syn_report(
        _FIXTURE_DIR / "messages_nested_warnings.rpt",
        ignore_file=_FIXTURE_DIR / "nested_one_ignored.txt",
    )
    assert summary.warnings_total == 3
    assert summary.warnings_ignored == 1
    assert summary.warnings_effective == 2


def test_check_syn_report_clean(capsys: pytest.CaptureFixture[str]) -> None:
    check_syn_report(_FIXTURE_DIR / "clean.syn.rpt")
    out = capsys.readouterr().out
    assert "Warnings: 0 (0 ignored)" in out
    assert "Critical warnings: 0 (0 ignored)" in out
    assert "Errors: 0" in out


def test_check_syn_report_rejects_warnings_legacy() -> None:
    with pytest.raises(SynReportError, match="Warnings: 2"):
        check_syn_report(_FIXTURE_DIR / "with_warnings.syn.rpt")


def test_check_syn_report_rejects_critical_legacy() -> None:
    with pytest.raises(SynReportError, match="Critical warnings: 1"):
        check_syn_report(_FIXTURE_DIR / "with_critical.syn.rpt")


def test_check_syn_report_rejects_errors_legacy() -> None:
    with pytest.raises(SynReportError, match="Errors: 3"):
        check_syn_report(_FIXTURE_DIR / "with_errors.syn.rpt")


def test_check_syn_report_rejects_errors_messages() -> None:
    with pytest.raises(SynReportError, match="Errors: 3"):
        check_syn_report(_FIXTURE_DIR / "messages_with_errors.rpt")


def test_check_syn_report_missing_summary() -> None:
    with pytest.raises(SynReportError, match="Could not parse"):
        check_syn_report(_FIXTURE_DIR / "missing_critical_line.syn.rpt")


def test_check_syn_report_messages_ignore_agilex_reset_release(
    capsys: pytest.CaptureFixture[str],
) -> None:
    check_syn_report(
        _FIXTURE_DIR / "table_with_allowlisted.rpt",
        ignore_file=_AGILEX_IGNORE,
    )
    out = capsys.readouterr().out
    assert "Warnings: 1 (1 ignored)" in out
    assert "Critical warnings: 1 (1 ignored)" in out
    assert "Errors: 0" in out


def test_check_syn_report_messages_rejects_warnings_without_ignore_file() -> None:
    summary = parse_syn_report(_FIXTURE_DIR / "table_with_allowlisted.rpt")
    assert summary.warnings_effective == 1
    assert summary.critical_effective == 1


def test_check_syn_report_messages_rejects_nested_warnings() -> None:
    with pytest.raises(SynReportError, match="Warnings: 3"):
        check_syn_report(_FIXTURE_DIR / "messages_nested_warnings.rpt")


def test_error_count_from_singular_warning_footer_legacy() -> None:
    summary = parse_syn_report(_FIXTURE_DIR / "singular_warning_footer.rpt")
    assert summary.errors == 0
