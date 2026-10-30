"""Serialize CSR register models to YAML."""

import yaml

from csr_gen.model import Field, Register, RegisterModel


def dump_model_yaml(model: RegisterModel) -> str:
    """Render a register model as YAML for inspection and golden tests."""
    document = {
        "registers": [_register_to_mapping(register) for register in model.registers]
    }
    return yaml.safe_dump(document, sort_keys=False)


def _register_to_mapping(register: Register) -> dict[str, object]:
    mapping: dict[str, object] = {
        "name": register.name,
        "address": register.address,
    }
    if register.address_end is not None:
        mapping["address_end"] = register.address_end
    mapping["description"] = register.description
    mapping["hw_access"] = register.hw_access
    mapping["fields"] = [
        _field_to_mapping(register_field) for register_field in register.fields
    ]
    return mapping


def _field_to_mapping(register_field: Field) -> dict[str, object]:
    return {
        "name": register_field.name,
        "msb": register_field.msb,
        "lsb": register_field.lsb,
        "access": register_field.access,
        "reset": register_field.reset,
        "description": register_field.description,
    }
