"""End-to-end: generate C headers from Markdown, compile and run C harnesses."""

import subprocess
from pathlib import Path

import pytest

_CASES = [
    "example-device",
    "external-device",
    "multi-subsection-tables",
    "optional-no-reset-column",
    "pqc-ip",
    "cca-accel",
]


@pytest.mark.parametrize("case", _CASES)
def test_c_header_compile_case(case: str) -> None:
    case_dir = Path(__file__).resolve().parent / case
    result = subprocess.run(
        ["make", "test"],
        check=False,
        cwd=case_dir,
    )
    assert result.returncode == 0, f"make test failed in {case_dir}"
