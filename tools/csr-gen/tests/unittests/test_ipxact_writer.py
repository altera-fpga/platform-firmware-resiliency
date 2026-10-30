from pathlib import Path

import pytest

from csr_gen.input.ipxact_reader import load_ipxact, load_ipxact_file
from csr_gen.input.markdown_reader import load_markdown_file
from csr_gen.input.yaml_reader import load_yaml_file
from csr_gen.model import Field, Register, RegisterModel
from csr_gen.output.ipxact_writer import write_ipxact, write_ipxact_file
from csr_gen.output.markdown_writer import write_markdown
from tests.unittests.model_compare import assert_models_equal

from test_paths import REPO_ROOT, TESTDATA

MINIMAL_XML = TESTDATA / "ipxact_minimal.xml"
EXTERNAL_DEVICE = REPO_ROOT / "specs" / "golden" / "external-device"
GOLDEN_ROOT = REPO_ROOT / "specs" / "golden"


@pytest.mark.parametrize(
    "case_name",
    ["example-device", "external-device"],
)
def test_golden_yaml_export_matches_expected_xml(case_name: str) -> None:
    case_dir = GOLDEN_ROOT / case_name
    model = load_yaml_file(case_dir / "model.yml")
    section = case_dir.joinpath("section.txt").read_text(encoding="utf-8").strip()
    expected = case_dir.joinpath("expected.xml").read_text(encoding="utf-8")
    assert write_ipxact(model, memory_map_name=section) == expected


def test_ipxact_round_trip(tmp_path) -> None:
    original = load_ipxact_file(MINIMAL_XML)
    output = tmp_path / "roundtrip.xml"
    write_ipxact_file(
        output,
        original.model,
        memory_map_name=original.memory_map_name,
    )
    restored = load_ipxact_file(output)
    assert_models_equal(original.model, restored.model)


def test_ipxact_export_unknown_access_defaults_to_read_write() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="STAT",
                address=0,
                description="Status",
                fields=[
                    Field(
                        name="FLAG",
                        msb=0,
                        lsb=0,
                        access="bogus",
                        reset=0,
                        description="Flag",
                    )
                ],
            )
        ]
    )
    xml = write_ipxact(model, memory_map_name="Map")
    assert xml.count("ipxact:access>read-write</ipxact:access>") == 2


def test_ipxact_export_uses_sanitized_identifiers_for_peakrdl() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0,
                description="Control",
                fields=[
                    Field(
                        name="ENABLE",
                        msb=0,
                        lsb=0,
                        access="rw",
                        reset=0,
                        description="Enable",
                    )
                ],
            )
        ]
    )
    xml = write_ipxact(model, memory_map_name="CSR Registers")
    assert "<ipxact:name>csr_registers</ipxact:name>" in xml
    assert "<ipxact:name>CSR Registers</ipxact:name>" not in xml
    assert "<ipxact:description>CSR Registers</ipxact:description>" in xml


def test_ipxact_import_to_markdown_round_trip(tmp_path: Path) -> None:
    original = load_ipxact_file(MINIMAL_XML)
    markdown = write_markdown(
        original.model,
        original.section_heading,
        section_heading=original.section_heading,
        heading_level=original.heading_level,
    )
    markdown_path = tmp_path / "roundtrip.md"
    markdown_path.write_text(markdown, encoding="utf-8")
    restored = load_markdown_file(markdown_path, original.section_heading)
    assert len(restored.model.registers) == len(original.model.registers)
    for original_register, restored_register in zip(
        original.model.registers, restored.model.registers, strict=True
    ):
        assert original_register.name == restored_register.name
        assert original_register.address == restored_register.address
        assert len(original_register.fields) == len(restored_register.fields)
        for original_field, restored_field in zip(
            original_register.fields, restored_register.fields, strict=True
        ):
            assert original_field.name == restored_field.name
            assert original_field.access == restored_field.access
            assert original_field.msb == restored_field.msb
            assert original_field.lsb == restored_field.lsb
            assert original_field.reset == restored_field.reset


def test_ipxact_export_preserves_external_range_and_hw_access() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="MEM",
                address=0x20,
                address_end=0x2F,
                hw_access="external",
                description="External memory",
                fields=[
                    Field(name="WINDOW", msb=31, lsb=0, access="rw", reset=0),
                ],
            )
        ]
    )
    xml = write_ipxact(model, memory_map_name="Map")
    assert "<ipxact:dim>4</ipxact:dim>" in xml
    assert "csrgen:hwAccess" in xml
    restored = load_ipxact_file_from_string(xml)
    register = restored.model.registers[0]
    assert register.address_end == 0x2F
    assert register.hw_access == "external"


def test_ipxact_export_preserves_none_and_r0w1c_access() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0,
                fields=[
                    Field(name="RSVD", msb=1, lsb=1, access="none", reset=0),
                    Field(name="FLAG", msb=0, lsb=0, access="r0w1c", reset=0),
                ],
            )
        ]
    )
    xml = write_ipxact(model, memory_map_name="Map")
    assert "csrgen:access" in xml
    restored = load_ipxact_file_from_string(xml)
    fields = {field.name: field for field in restored.model.registers[0].fields}
    assert fields["RSVD"].access == "none"
    assert fields["FLAG"].access == "r0w1c"


def test_external_device_ipxact_golden_round_trip() -> None:
    original = load_markdown_file(
        EXTERNAL_DEVICE / "regs.md",
        "CSR Registers",
    )
    xml = write_ipxact(
        original.model,
        memory_map_name=original.section_heading,
    )
    restored = load_ipxact_file_from_string(xml)
    assert_models_equal(original.model, restored.model)


def load_ipxact_file_from_string(xml: str):
    from csr_gen.input.ipxact_reader import load_ipxact

    return load_ipxact(xml, "<string>")
