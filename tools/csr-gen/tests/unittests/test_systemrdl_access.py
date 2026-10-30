import pytest

from csr_gen.systemrdl.access import (
    access_from_rdl_properties,
    field_access_properties,
    rdl_escape_string,
    rdl_identifier,
)


class _Enum:
    def __init__(self, name: str) -> None:
        self.name = name


@pytest.mark.parametrize(
    ("access", "sw", "onread", "onwrite", "hw"),
    [
        ("none", "r", None, None, "r"),
        ("ro", "r", None, None, "r"),
        ("rc", "r", "rclr", None, "r"),
        ("rw", "rw", None, None, "rw"),
        ("wo", "w", None, None, "r"),
        ("r0w1c", "rw", "rclr", "woset", "rw"),
        ("rw1s", "rw", None, "woset", "rw"),
        ("rw1c", "rw", None, "woclr", "rw"),
        ("rw0c", "rw", None, "wzc", "rw"),
    ],
)
def test_field_access_properties(access, sw, onread, onwrite, hw) -> None:
    assert field_access_properties(access) == (sw, onread, onwrite, hw)


def test_field_access_properties_rejects_unknown_access() -> None:
    with pytest.raises(ValueError, match="Unsupported field access"):
        field_access_properties("bogus")


@pytest.mark.parametrize(
    ("csr_gen_access", "sw", "onread", "onwrite", "expected"),
    [
        ("none", None, None, None, "none"),
        (None, _Enum("r"), _Enum("rclr"), None, "rc"),
        (None, _Enum("rw"), None, _Enum("woclr"), "rw1c"),
        (None, _Enum("rw"), None, _Enum("woset"), "rw1s"),
        (None, _Enum("rw"), None, _Enum("wzc"), "rw0c"),
        (None, _Enum("rw"), _Enum("rclr"), _Enum("woset"), "r0w1c"),
        (None, _Enum("w"), None, None, "wo"),
        (None, _Enum("rw"), None, None, "rw"),
        (None, _Enum("r"), None, None, "ro"),
        (None, "AccessType.rw", None, None, "rw"),
    ],
)
def test_access_from_rdl_properties(
    csr_gen_access, sw, onread, onwrite, expected
) -> None:
    assert (
        access_from_rdl_properties(
            csr_gen_access=csr_gen_access,
            sw=sw,
            onread=onread,
            onwrite=onwrite,
        )
        == expected
    )


def test_access_from_rdl_properties_rejects_unknown_combination() -> None:
    with pytest.raises(ValueError, match="Unsupported SystemRDL field access"):
        access_from_rdl_properties(
            csr_gen_access=None,
            sw=_Enum("na"),
            onread=None,
            onwrite=None,
        )


def test_access_from_rdl_properties_accepts_plain_string_sw() -> None:
    assert (
        access_from_rdl_properties(
            csr_gen_access=None,
            sw="r",
            onread=None,
            onwrite=None,
        )
        == "ro"
    )


def test_rdl_identifier_sanitizes_invalid_characters() -> None:
    assert rdl_identifier("A-B") == "A_B"
    assert rdl_identifier("1REG") == "_1REG"


def test_rdl_identifier_prefixes_lowercase_keywords() -> None:
    assert rdl_identifier("mem") == "_mem"
    assert rdl_identifier("MEM") == "MEM"


def test_rdl_identifier_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        rdl_identifier("   ")


def test_enum_name_without_name_attribute() -> None:
    assert (
        access_from_rdl_properties(
            csr_gen_access=None,
            sw=type("Sw", (), {"__str__": lambda self: "AccessType.rw"})(),
            onread=None,
            onwrite=None,
        )
        == "rw"
    )


def test_rdl_escape_string() -> None:
    assert rdl_escape_string('say "hi"\\now') == 'say \\"hi\\"\\\\now'
