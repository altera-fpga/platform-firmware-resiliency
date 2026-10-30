"""Tests for GUI table row conversion."""

from pathlib import Path

from csr_gen.input.markdown_reader import load_markdown_file
from csr_gen.model import RegisterModel
from csr_gen_gui.model_table import (
    make_ranged_external_register,
    model_to_row_dicts,
    row_dicts_to_model,
)

GOLDEN = Path(__file__).resolve().parents[2] / "specs" / "golden" / "example-device"


def test_model_table_round_trip_example_device() -> None:
    model = load_markdown_file(GOLDEN / "regs.md", "CSR Registers").model
    rows = model_to_row_dicts(model)
    round_tripped, errors = row_dicts_to_model(rows)
    assert errors == []
    assert round_tripped is not None
    assert len(round_tripped.registers) == len(model.registers)
    assert round_tripped.registers[0].name == "CTRL"
    assert round_tripped.registers[0].fields[1].name == "MODE"


def test_ranged_external_register_is_valid() -> None:
    register = make_ranged_external_register(
        name="MEM",
        address_start=0x20,
        address_end=0x2F,
        field_name="WINDOW",
        access="rw",
        reset=0,
        description="Memory window",
    )
    model, errors = row_dicts_to_model(
        model_to_row_dicts(RegisterModel(registers=[register]))
    )
    assert errors == []
    assert model is not None
    assert model.registers[0].address_end == 0x2F
    assert model.registers[0].hw_access == "external"


def test_row_dicts_to_model_allows_empty_register_for_editor() -> None:
    rows = [
        {
            "register": "NEW_REG",
            "address": "0x10",
            "field": "",
            "bits": "",
            "access": "",
            "reset": "",
            "hw access": "internal",
            "description": "New register",
        }
    ]
    model, errors = row_dicts_to_model(rows, allow_incomplete=True)
    assert model is not None
    assert len(model.registers) == 1
    assert model.registers[0].fields == []
    assert errors == []

    from csr_gen.model import collect_model_errors

    assert any(
        "must contain at least one field" in error
        for error in collect_model_errors(model)
    )

    strict_model, strict_errors = row_dicts_to_model(rows)
    assert strict_model is None
    assert strict_errors
