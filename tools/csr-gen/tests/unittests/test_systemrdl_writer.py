from pathlib import Path

import pytest

from csr_gen.input.systemrdl_reader import load_systemrdl_file
from csr_gen.input.yaml_reader import load_yaml_file
from csr_gen.model import Field, Register, RegisterModel
from csr_gen.output.systemrdl_writer import (
    SystemRdlGenerationError,
    write_systemrdl,
    write_systemrdl_file,
)
from model_compare import assert_models_equal

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_ROOT = REPO_ROOT / "specs" / "golden"


@pytest.mark.parametrize(
    "case_name",
    ["example-device", "external-device"],
)
def test_golden_yaml_export_matches_expected_rdl(case_name: str) -> None:
    case_dir = GOLDEN_ROOT / case_name
    model = load_yaml_file(case_dir / "model.yml")
    section = case_dir.joinpath("section.txt").read_text(encoding="utf-8").strip()
    expected = case_dir.joinpath("expected.rdl").read_text(encoding="utf-8")
    assert write_systemrdl(model, section_heading=section) == expected


def test_systemrdl_round_trip(tmp_path: Path) -> None:
    case_dir = GOLDEN_ROOT / "example-device"
    model = load_yaml_file(case_dir / "model.yml")
    section = case_dir.joinpath("section.txt").read_text(encoding="utf-8").strip()
    output = tmp_path / "roundtrip.rdl"
    write_systemrdl_file(output, model, section_heading=section)
    restored = load_systemrdl_file(output)
    assert_models_equal(model, restored.model)


def test_write_systemrdl_rejects_empty_section_heading() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0,
                description="",
                fields=[Field(name="A", msb=0, lsb=0, access="rw", reset=0)],
            )
        ]
    )
    with pytest.raises(SystemRdlGenerationError, match="section heading"):
        write_systemrdl(model, section_heading="  ")


def test_write_systemrdl_renders_external_and_ranged_registers() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="MEM",
                address=0x20,
                address_end=0x2F,
                description="External memory",
                hw_access="external",
                fields=[
                    Field(
                        name="WINDOW",
                        msb=31,
                        lsb=0,
                        access="rw",
                        reset=0,
                        description="Window",
                    )
                ],
            )
        ]
    )
    rdl = write_systemrdl(model, section_heading="CSR Registers")
    assert "external reg" in rdl
    assert "MEM[4] @ 0x20 += 0x4;" in rdl
    assert "csr_gen_address_end" not in rdl
    assert 'desc = "External memory";' in rdl


def test_write_systemrdl_renders_onread_and_onwrite_properties() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="STAT",
                address=0,
                description="",
                fields=[
                    Field(name="FLAG", msb=0, lsb=0, access="rc", reset=0),
                    Field(name="CTRL", msb=1, lsb=1, access="rw0c", reset=0),
                ],
            )
        ]
    )
    rdl = write_systemrdl(model, section_heading="CSR Registers")
    assert "onread = rclr;" in rdl
    assert "onwrite = wzc;" in rdl
