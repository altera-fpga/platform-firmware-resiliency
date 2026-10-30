"""Read CSR register models from YAML test and interchange files."""

from collections.abc import Mapping
from pathlib import Path

import yaml

from csr_gen.errors import YamlParseError
from csr_gen.model import (
    DEFAULT_HW_ACCESS,
    Field,
    Register,
    RegisterModel,
    validate_model,
)


def load_yaml_file(path: Path) -> RegisterModel:
    """Read and validate a CSR register model from a YAML file."""
    return load_yaml(path.read_text(encoding="utf-8"))


def load_yaml(yaml_text: str) -> RegisterModel:
    """Read and validate a CSR register model from a YAML string."""
    try:
        document = yaml.safe_load(yaml_text)
    except yaml.YAMLError as error:
        raise YamlParseError(f"Unable to parse YAML: {error}") from error
    if not isinstance(document, Mapping) or not isinstance(
        document.get("registers"), list
    ):
        raise YamlParseError("YAML document must contain a registers list.")

    registers = [
        _parse_register(register, index)
        for index, register in enumerate(document["registers"], start=1)
    ]
    model = RegisterModel(registers=registers)
    validate_model(model)
    return model


def _parse_register(value: object, index: int) -> Register:
    register = _require_mapping(value, f"register {index}")
    fields = register.get("fields")
    if not isinstance(fields, list):
        raise YamlParseError(f"YAML register {index} must contain a fields list.")
    return Register(
        name=_require_string(register, "name", f"register {index}"),
        address=_require_integer(register, "address", f"register {index}"),
        description=_optional_string(register, "description", f"register {index}"),
        hw_access=_optional_hw_access(register, f"register {index}"),
        address_end=_optional_integer(register, "address_end", f"register {index}"),
        fields=[
            _parse_field(register_field, f"register {index} field {field_index}")
            for field_index, register_field in enumerate(fields, start=1)
        ],
    )


def _parse_field(value: object, context: str) -> Field:
    register_field = _require_mapping(value, context)
    return Field(
        name=_require_string(register_field, "name", context),
        msb=_require_integer(register_field, "msb", context),
        lsb=_require_integer(register_field, "lsb", context),
        access=_require_string(register_field, "access", context),
        reset=_require_integer(register_field, "reset", context),
        description=_optional_string(register_field, "description", context),
    )


def _require_mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise YamlParseError(f"YAML {context} must be a mapping.")
    return value


def _require_string(mapping: Mapping[str, object], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        raise YamlParseError(f"YAML {context} {key} must be a string.")
    return value


def _optional_string(mapping: Mapping[str, object], key: str, context: str) -> str:
    value = mapping.get(key, "")
    if not isinstance(value, str):
        raise YamlParseError(f"YAML {context} {key} must be a string.")
    return value


def _optional_hw_access(mapping: Mapping[str, object], context: str) -> str:
    value = mapping.get("hw_access", DEFAULT_HW_ACCESS)
    if not isinstance(value, str):
        raise YamlParseError(f"YAML {context} hw_access must be a string.")
    return value


def _optional_integer(
    mapping: Mapping[str, object], key: str, context: str
) -> int | None:
    if key not in mapping:
        return None
    return _require_integer(mapping, key, context)


def _require_integer(mapping: Mapping[str, object], key: str, context: str) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise YamlParseError(f"YAML {context} {key} must be an integer.")
    return value
