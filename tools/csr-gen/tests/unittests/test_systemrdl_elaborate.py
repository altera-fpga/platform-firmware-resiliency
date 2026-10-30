from pathlib import Path

import pytest

pytest.importorskip("systemrdl")

from systemrdl import RDLCompiler

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_ROOT = REPO_ROOT / "specs" / "golden"


def _golden_rdl_cases() -> list[Path]:
    return sorted(GOLDEN_ROOT.glob("*/expected.rdl"))


@pytest.mark.parametrize(
    "rdl_path", _golden_rdl_cases(), ids=lambda path: path.parent.name
)
def test_golden_systemrdl_elaborates(rdl_path: Path) -> None:
    compiler = RDLCompiler()
    compiler.compile_file(str(rdl_path))
    compiler.elaborate()


def test_generated_systemrdl_from_writer_elaborates(tmp_path: Path) -> None:
    from csr_gen.input.yaml_reader import load_yaml_file
    from csr_gen.output.systemrdl_writer import write_systemrdl_file

    case_dir = GOLDEN_ROOT / "example-device"
    model = load_yaml_file(case_dir / "model.yml")
    section = case_dir.joinpath("section.txt").read_text(encoding="utf-8").strip()
    output = tmp_path / "generated.rdl"
    write_systemrdl_file(output, model, section_heading=section)

    compiler = RDLCompiler()
    compiler.compile_file(str(output))
    compiler.elaborate()
