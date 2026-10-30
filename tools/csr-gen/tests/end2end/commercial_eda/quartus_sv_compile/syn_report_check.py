"""Parse Quartus synthesis reports; fail on warnings or critical warnings."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Default ignore list filename in each synthesis case directory.
IGNORED_SYN_MESSAGES_FILENAME = "ignored_syn_messages.txt"

# Legacy summary lines when the report has no Synthesis Messages section.
_LEGACY_CRITICAL = re.compile(r";\s*Critical Warnings\s*:\s*(\d+)\b", re.IGNORECASE)
_LEGACY_WARNINGS = re.compile(r";\s*Warnings\s*:\s*(\d+)\b", re.IGNORECASE)
_LEGACY_ERRORS = re.compile(r";\s*Errors\s*:\s*(\d+)\b", re.IGNORECASE)

_SYNTHESIS_MESSAGES_SECTION = re.compile(
    r";\s*Synthesis Messages\s*;\s*\n\+[-+]+\+\s*\n(.*)\Z",
    re.DOTALL,
)

_MESSAGE_LINE_START = re.compile(r"^(Error|Critical Warning|Warning)\s+\(\d+\):")


class SynReportError(Exception):
    """Raised when a synthesis report violates policy."""


@dataclass(frozen=True)
class SynReportSummary:
    """Counts parsed from a Quartus synthesis report."""

    warnings_total: int
    warnings_ignored: int
    critical_total: int
    critical_ignored: int
    errors: int

    @property
    def warnings_effective(self) -> int:
        return self.warnings_total - self.warnings_ignored

    @property
    def critical_effective(self) -> int:
        return self.critical_total - self.critical_ignored

    def report_lines(self) -> tuple[str, str, str]:
        return (
            f"Warnings: {self.warnings_total} ({self.warnings_ignored} ignored)",
            f"Critical warnings: {self.critical_total} ({self.critical_ignored} ignored)",
            f"Errors: {self.errors}",
        )


def load_ignored_message_prefixes(path: Path | None) -> tuple[str, ...]:
    """Load line-prefix strings from a case ignore file (blank lines and # comments skipped)."""
    if path is None or not path.is_file():
        return ()
    prefixes: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        prefixes.append(stripped)
    return tuple(sorted(prefixes, key=len, reverse=True))


def parse_syn_report(
    path: Path,
    *,
    ignore_file: Path | None = None,
) -> SynReportSummary:
    """Parse warning, critical warning, and error counts from a synthesis report."""
    if not path.is_file():
        raise SynReportError(f"Synthesis report not found: {path}")

    ignore_prefixes = load_ignored_message_prefixes(ignore_file)
    text = path.read_text(encoding="utf-8", errors="replace")
    section = _synthesis_messages_text(text)
    if section is not None:
        return _counts_from_messages(section, ignore_prefixes)

    summary = _legacy_summary(text)
    if summary is None:
        raise SynReportError(
            f"Could not parse {path}: no '; Synthesis Messages ;' section and "
            "no legacy '; Warnings:' / '; Critical Warnings:' / '; Errors:' lines"
        )
    return summary


def check_syn_report(
    path: Path,
    *,
    ignore_file: Path | None = None,
) -> SynReportSummary:
    """Print summary counts; fail if effective warnings, critical warnings, or errors."""
    summary = parse_syn_report(path, ignore_file=ignore_file)
    for line in summary.report_lines():
        print(line, file=sys.stdout)

    if summary.errors != 0:
        raise SynReportError(f"Errors: {summary.errors} (expected 0) in {path}")
    if summary.critical_effective != 0:
        raise SynReportError(
            f"Critical warnings: {summary.critical_effective} "
            f"({summary.critical_ignored} ignored, {summary.critical_total} total) "
            f"(expected 0 effective) in {path}"
        )
    if summary.warnings_effective != 0:
        raise SynReportError(
            f"Warnings: {summary.warnings_effective} "
            f"({summary.warnings_ignored} ignored, {summary.warnings_total} total) "
            f"(expected 0 effective) in {path}"
        )
    return summary


def _synthesis_messages_text(text: str) -> str | None:
    match = _SYNTHESIS_MESSAGES_SECTION.search(text)
    if match is None:
        return None
    return match.group(1)


def _counts_from_messages(
    section: str,
    ignore_prefixes: tuple[str, ...],
) -> SynReportSummary:
    warnings_total = 0
    warnings_ignored = 0
    critical_total = 0
    critical_ignored = 0
    errors = 0

    for line in section.splitlines():
        stripped = line.lstrip()
        match = _MESSAGE_LINE_START.match(stripped)
        if match is None:
            continue
        ignored = _line_matches_ignore_prefix(stripped, ignore_prefixes)
        severity = match.group(1)

        if severity == "Error":
            errors += 1
        elif severity == "Critical Warning":
            critical_total += 1
            if ignored:
                critical_ignored += 1
        else:
            warnings_total += 1
            if ignored:
                warnings_ignored += 1

    return SynReportSummary(
        warnings_total=warnings_total,
        warnings_ignored=warnings_ignored,
        critical_total=critical_total,
        critical_ignored=critical_ignored,
        errors=errors,
    )


def _line_matches_ignore_prefix(
    line: str,
    ignore_prefixes: tuple[str, ...],
) -> bool:
    for prefix in ignore_prefixes:
        if line.startswith(prefix):
            return True
    return False


def _legacy_summary(text: str) -> SynReportSummary | None:
    has_critical = _LEGACY_CRITICAL.search(text) is not None
    has_warnings = _LEGACY_WARNINGS.search(text) is not None
    has_errors = _LEGACY_ERRORS.search(text) is not None
    if not (has_critical and has_warnings and has_errors):
        return None

    return SynReportSummary(
        warnings_total=_legacy_count(text, _LEGACY_WARNINGS) or 0,
        warnings_ignored=0,
        critical_total=_legacy_count(text, _LEGACY_CRITICAL) or 0,
        critical_ignored=0,
        errors=_legacy_count(text, _LEGACY_ERRORS) or 0,
    )


def _legacy_count(text: str, pattern: re.Pattern[str]) -> int | None:
    matches = [int(match.group(1)) for match in pattern.finditer(text)]
    if matches:
        return max(matches)
    return None


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) not in (1, 2):
        print(
            f"usage: {Path(__file__).name} <path/to/test.syn.rpt> "
            f"[path/to/{IGNORED_SYN_MESSAGES_FILENAME}]",
            file=sys.stderr,
        )
        return 2
    ignore_file = Path(args[1]) if len(args) == 2 else None
    try:
        check_syn_report(Path(args[0]), ignore_file=ignore_file)
    except SynReportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
