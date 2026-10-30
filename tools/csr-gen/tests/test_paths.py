"""Shared filesystem paths for unit and end2end tests."""

from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
TESTDATA = TESTS_DIR / "testdata"
REPO_ROOT = TESTS_DIR.parent
