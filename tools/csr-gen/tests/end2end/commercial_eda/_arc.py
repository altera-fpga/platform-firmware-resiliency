"""Helpers for commercial EDA pytest wrappers (Quartus, VCS, Simics)."""

from __future__ import annotations

import shutil
from pathlib import Path

_HINT_FILE = (
    Path(__file__).resolve().parents[3] / "docs" / "not_shipped" / "eda-tool-hint.txt"
)


def require_tool(name: str) -> None:
    """Fail pytest when a commercial EDA tool is missing from PATH."""
    if shutil.which(name) is not None:
        return

    message = f"{name} not found on PATH. Install the tool and put it on PATH."
    if _HINT_FILE.is_file():
        hint = _HINT_FILE.read_text(encoding="utf-8").strip()
        if hint:
            message = f"{message}\n{hint}"
    raise AssertionError(message)
