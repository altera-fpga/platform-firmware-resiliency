"""Document Accellera generic_rdl import limits (expected failure)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
GENERIC_RDL = (
    REPO_ROOT
    / "tests"
    / "testdata"
    / "systemrdl"
    / "SystemRDL_1.0"
    / "Examples"
    / "generic_rdl"
    / "generic_example.rdl"
)
CSR_GEN = [sys.executable, "-m", "csr_gen"]


def test_generic_rdl_import_is_not_supported(tmp_path: Path) -> None:
    """generic_example.rdl uses signals, Perl, and mem — outside the flat subset."""
    markdown_output = tmp_path / "generic.md"
    result = subprocess.run(
        [
            *CSR_GEN,
            "generate",
            "--input-file",
            str(GENERIC_RDL),
            "--input-format",
            "systemrdl",
            "--output-file",
            str(markdown_output),
            "--output-format",
            "markdown",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not markdown_output.exists()
