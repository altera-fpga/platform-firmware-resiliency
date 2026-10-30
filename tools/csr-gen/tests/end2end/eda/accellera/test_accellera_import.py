"""End-to-end SystemRDL import tests for Accellera 1.0 spec examples."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
EXAMPLES_ROOT = (
    REPO_ROOT / "tests" / "testdata" / "systemrdl" / "SystemRDL_1.0" / "Examples"
)
CSR_GEN = [sys.executable, "-m", "csr_gen"]


@dataclass(frozen=True)
class AccelleraImportCase:
    case_id: str
    rdl_relpath: str
    min_registers: int
    addrmap_instance: str | None = None


ACCELLERA_IMPORT_CASES = [
    AccelleraImportCase(
        "counter-example",
        "incr_cntr_test/counter_example.rdl",
        min_registers=1,
    ),
    AccelleraImportCase(
        "lock-and-key",
        "lock_and_key/lock_and_key.rdl",
        min_registers=2,
    ),
    AccelleraImportCase(
        "leon2-uart",
        "Leon2/uart.rdl",
        min_registers=4,
    ),
    AccelleraImportCase(
        "leon2-gpio",
        "Leon2/gpio.rdl",
        min_registers=2,
    ),
]


@pytest.mark.parametrize("case", ACCELLERA_IMPORT_CASES, ids=lambda c: c.case_id)
def test_accellera_rdl_imports_to_markdown(
    case: AccelleraImportCase, tmp_path: Path
) -> None:
    rdl_path = EXAMPLES_ROOT / case.rdl_relpath
    markdown_output = tmp_path / f"{case.case_id}.md"

    command = [
        *CSR_GEN,
        "generate",
        "--input-file",
        str(rdl_path),
        "--input-format",
        "systemrdl",
        "--output-file",
        str(markdown_output),
        "--output-format",
        "markdown",
    ]
    if case.addrmap_instance is not None:
        command.extend(["--systemrdl-addrmap", case.addrmap_instance])

    result = subprocess.run(command, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr or result.stdout

    markdown = markdown_output.read_text(encoding="utf-8")
    assert markdown.startswith("## "), "Markdown export must include a section heading"
    assert "| Register | Address | Field | Bits |" in markdown
    assert markdown.count("| Register | Address | Field | Bits |") >= 1

    validate = subprocess.run(
        [
            *CSR_GEN,
            "validate",
            "--input-file",
            str(markdown_output),
            "--input-format",
            "markdown",
            "--markdown-section",
            markdown.splitlines()[0].lstrip("# ").strip(),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert validate.returncode == 0, validate.stderr or validate.stdout

    from csr_gen.input.markdown_reader import load_markdown_file

    section = markdown.splitlines()[0].lstrip("# ").strip()
    spec = load_markdown_file(markdown_output, section)
    assert len(spec.model.registers) >= case.min_registers
