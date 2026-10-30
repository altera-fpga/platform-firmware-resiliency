"""Commercial EDA: Quartus synthesis of generated CSR SystemVerilog."""

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
def test_quartus_sv_compile_case(case: str) -> None:
    require_tool("quartus_syn")

    case_dir = Path(__file__).resolve().parent / case
    script = case_dir / "test.sh"
    result = subprocess.run(
        [str(script)],
        check=False,
        cwd=case_dir,
    )
    assert result.returncode == 0, f"{script} failed in {case_dir}"
