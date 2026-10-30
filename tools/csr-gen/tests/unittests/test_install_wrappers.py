"""Tests for install wrapper script generation."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WRITE_INSTALL_WRAPPER = REPO_ROOT / "scripts" / "write_install_wrapper.sh"


def test_write_install_wrapper_execs_venv_binary(tmp_path: Path) -> None:
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    executable = venv_bin / "csr-gen"
    executable.write_text("#!/bin/sh\nprintf 'csr-gen-ok\\n'\n", encoding="utf-8")
    executable.chmod(0o755)

    wrapper = tmp_path / "bin" / "csr-gen"
    subprocess.run(
        [str(WRITE_INSTALL_WRAPPER), str(wrapper), "csr-gen"],
        check=True,
    )

    result = subprocess.run(
        [str(wrapper)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "csr-gen-ok"
