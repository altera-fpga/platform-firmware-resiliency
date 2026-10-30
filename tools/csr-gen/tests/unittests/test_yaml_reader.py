from pathlib import Path

import pytest

from csr_gen.errors import ModelValidationError, YamlParseError
from csr_gen.input.yaml_reader import load_yaml, load_yaml_file

from test_paths import TESTDATA


def test_load_yaml_creates_normalized_model() -> None:
    model = load_yaml("""\
registers:
  - name: ctrl
    address: 0x00
    description: Control register
    fields:
      - name: enable
        msb: 0
        lsb: 0
        access: RW
        reset: 0
""")

    register = model.registers[0]
    assert register.name == "CTRL"
    assert register.description == "Control register"
    assert register.fields[0].name == "ENABLE"
    assert register.fields[0].access == "rw"
    assert register.fields[0].description == ""


def test_load_yaml_file_reads_yml_model() -> None:
    model = load_yaml_file(TESTDATA / "valid_registers.yml")

    assert model.registers[0].name == "CTRL"


@pytest.mark.parametrize(
    ("yaml_text", "message"),
    [
        ("registers: [", "Unable to parse YAML"),
        ("other: []", "registers list"),
        ("registers:\n  - ctrl", "must be a mapping"),
        ("registers:\n  - name: CTRL\n    address: 0\n", "fields list"),
        (
            """\
registers:
  - name: CTRL
    address: 0
    fields:
      - enable
""",
            "field 1 must be a mapping",
        ),
        (
            """\
registers:
  - name: CTRL
    address: nope
    fields: []
""",
            "address must be an integer",
        ),
        (
            """\
registers:
  - name: CTRL
    address: 0
    description: 1
    fields: []
""",
            "description must be a string",
        ),
        (
            """\
registers:
  - name: CTRL
    address: 0
    fields:
      - msb: 0
        lsb: 0
        access: rw
        reset: 0
""",
            "name must be a string",
        ),
        (
            """\
registers:
  - name: CTRL
    address: 0
    hw_access: 1
    fields:
      - name: EN
        msb: 0
        lsb: 0
        access: rw
        reset: 0
""",
            "hw_access must be a string",
        ),
    ],
)
def test_load_yaml_rejects_malformed_schema(yaml_text: str, message: str) -> None:
    with pytest.raises(YamlParseError, match=message):
        load_yaml(yaml_text)


def test_load_yaml_runs_shared_legality_checks() -> None:
    with pytest.raises(ModelValidationError, match="must contain at least one field"):
        load_yaml("""\
registers:
  - name: CTRL
    address: 0
    fields: []
""")
