"""Validate repository golden CSV CSR specifications."""

from pathlib import Path

import pytest

from csr_gen.input.csv_reader import load_csv_file
from csr_gen.input.yaml_reader import load_yaml_file
from csr_gen.output.csv_writer import write_csv
from model_compare import assert_models_equal

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_CSV_ROOT = REPO_ROOT / "specs" / "golden" / "csv"


def _golden_csv_case_dirs() -> list[Path]:
    if not GOLDEN_CSV_ROOT.is_dir():
        return []
    return sorted(path for path in GOLDEN_CSV_ROOT.iterdir() if path.is_dir())


def _read_csr_name(case_dir: Path) -> str | None:
    path = case_dir / "csr-name.txt"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip()


def _load_regs_csv(case_dir: Path):
    csr_name = _read_csr_name(case_dir)
    return load_csv_file(case_dir / "regs.csv", csr_name=csr_name)


@pytest.mark.parametrize(
    "case_dir", _golden_csv_case_dirs(), ids=lambda path: path.name
)
def test_golden_csv_regs_matches_model(case_dir: Path) -> None:
    """regs.csv and model.yml describe the same register model."""
    assert (case_dir / "regs.csv").is_file(), f"{case_dir} must contain regs.csv"
    assert (case_dir / "model.yml").is_file(), f"{case_dir} must contain model.yml"

    csv_spec = _load_regs_csv(case_dir)
    yaml_model = load_yaml_file(case_dir / "model.yml")
    assert_models_equal(csv_spec.model, yaml_model)


@pytest.mark.parametrize(
    "case_dir", _golden_csv_case_dirs(), ids=lambda path: path.name
)
def test_golden_csv_yaml_export_matches_expected(case_dir: Path) -> None:
    """model.yml -> CSV export matches expected.csv (generator only)."""
    assert (case_dir / "model.yml").is_file(), f"{case_dir} must contain model.yml"
    assert (
        case_dir / "expected.csv"
    ).is_file(), f"{case_dir} must contain expected.csv"

    model = load_yaml_file(case_dir / "model.yml")
    expected = (case_dir / "expected.csv").read_text(encoding="utf-8")
    assert write_csv(model) == expected


@pytest.mark.parametrize(
    "case_dir", _golden_csv_case_dirs(), ids=lambda path: path.name
)
def test_golden_csv_expected_round_trip(case_dir: Path) -> None:
    """expected.csv -> model -> CSV is idempotent (canonical parser + writer)."""
    assert (
        case_dir / "expected.csv"
    ).is_file(), f"{case_dir} must contain expected.csv"

    csr_name = _read_csr_name(case_dir)
    expected = (case_dir / "expected.csv").read_text(encoding="utf-8")
    spec = load_csv_file(case_dir / "expected.csv", csr_name=csr_name)
    assert write_csv(spec.model) == expected


@pytest.mark.parametrize(
    "case_dir", _golden_csv_case_dirs(), ids=lambda path: path.name
)
def test_golden_csv_regs_export_matches_expected(case_dir: Path) -> None:
    """regs.csv -> model -> CSV matches expected.csv (integrated import + export)."""
    assert (case_dir / "regs.csv").is_file(), f"{case_dir} must contain regs.csv"
    assert (
        case_dir / "expected.csv"
    ).is_file(), f"{case_dir} must contain expected.csv"

    spec = _load_regs_csv(case_dir)
    expected = (case_dir / "expected.csv").read_text(encoding="utf-8")
    assert write_csv(spec.model) == expected
