# Shared test fixtures

Inputs in this directory are used by unit tests under `tests/unittests/` and by
end-to-end tests under `tests/end2end/`. Import paths in Python tests via
`tests/test_paths.py` (`from test_paths import TESTDATA`).

Golden product examples live under `specs/golden/`; `tests/testdata/` holds
focused parser and integration fixtures (Markdown edge cases, IP-XACT samples,
SystemRDL hierarchy examples, and similar).
