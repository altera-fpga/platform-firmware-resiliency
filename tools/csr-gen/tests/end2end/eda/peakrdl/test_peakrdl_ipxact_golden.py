"""PeakRDL smoke tests for golden IP-XACT oracles exported by csr-gen."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("peakrdl")

REPO_ROOT = Path(__file__).resolve().parents[4]
GOLDEN_ROOT = REPO_ROOT / "specs" / "golden"


def _golden_ipxact_cases() -> list[Path]:
    return sorted(GOLDEN_ROOT.glob("*/expected.xml"))


def _peakrdl_executable() -> str:
    venv_candidate = Path(sys.executable).with_name("peakrdl")
    if venv_candidate.is_file():
        return str(venv_candidate)
    executable = shutil.which("peakrdl")
    if executable is None:
        pytest.skip("peakrdl executable is not on PATH")
    return executable


@pytest.mark.parametrize(
    "xml_path", _golden_ipxact_cases(), ids=lambda path: path.parent.name
)
def test_peakrdl_dump_imports_golden_ipxact(xml_path: Path) -> None:
    result = subprocess.run(
        [_peakrdl_executable(), "dump", str(xml_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert result.stdout.strip(), "peakrdl dump produced no output"
    assert "0x" in result.stdout
