"""Opt-in PeakRDL smoke tests for golden SystemRDL oracles."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("peakrdl")

REPO_ROOT = Path(__file__).resolve().parents[4]
GOLDEN_ROOT = REPO_ROOT / "specs" / "golden"


def _golden_rdl_cases() -> list[Path]:
    return sorted(GOLDEN_ROOT.glob("*/expected.rdl"))


def _peakrdl_executable() -> str:
    venv_candidate = Path(sys.executable).with_name("peakrdl")
    if venv_candidate.is_file():
        return str(venv_candidate)
    executable = shutil.which("peakrdl")
    if executable is None:
        pytest.skip("peakrdl executable is not on PATH")
    return executable


@pytest.mark.parametrize(
    "rdl_path", _golden_rdl_cases(), ids=lambda path: path.parent.name
)
def test_peakrdl_html_generates_documentation(rdl_path: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / f"{rdl_path.parent.name}-html"
    result = subprocess.run(
        [
            _peakrdl_executable(),
            "html",
            "-o",
            str(output_dir),
            str(rdl_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert any(output_dir.iterdir()), "PeakRDL html did not write any output"


@pytest.mark.parametrize(
    "rdl_path", _golden_rdl_cases(), ids=lambda path: path.parent.name
)
def test_peakrdl_regblock_generates_rtl(rdl_path: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / f"{rdl_path.parent.name}-regblock"
    output_dir.mkdir()
    result = subprocess.run(
        [
            _peakrdl_executable(),
            "regblock",
            "-o",
            str(output_dir),
            str(rdl_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    generated = list(output_dir.glob("*.sv")) + list(output_dir.glob("*.v"))
    assert generated, "PeakRDL regblock did not write SystemVerilog output"
