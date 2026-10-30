"""Commercial EDA: VCS functional simulation of generated CSR SystemVerilog."""

import subprocess
from pathlib import Path

import pytest

from tests.end2end.commercial_eda._arc import require_tool

_CASES = [
    "example-device",
    "external-device",
    "cca-accel",
]


@pytest.mark.parametrize("case", _CASES)
def test_vcs_sim_case(case: str) -> None:
    require_tool("vcs")

    case_dir = Path(__file__).resolve().parent / case
    script = case_dir / "test.sh"
    result = subprocess.run(
        [str(script)],
        check=False,
        cwd=case_dir,
    )
    assert result.returncode == 0, f"{script} failed in {case_dir}"
