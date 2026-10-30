import pytest

from csr_gen.errors import ModelValidationError
from csr_gen.model import (
    SUPPORTED_ACCESS,
    Field,
    FieldDraft,
    Register,
    RegisterDraft,
    RegisterModel,
    collect_register_draft_errors,
    register_decoder_addr_width,
    register_decoder_byte_high,
    register_has_address_range,
    register_is_external,
    register_occupied_offsets,
    register_range_index_width,
    register_slot_count,
    validate_model,
)


def _model(
    *,
    register_name: str = "CTRL",
    address: object = 0,
    field_name: str = "ENABLE",
    msb: object = 0,
    lsb: object = 0,
    reset: object = 0,
) -> RegisterModel:
    return RegisterModel(
        registers=[
            Register(
                name=register_name,
                address=address,  # type: ignore[arg-type]
                fields=[
                    Field(
                        name=field_name,
                        msb=msb,  # type: ignore[arg-type]
                        lsb=lsb,  # type: ignore[arg-type]
                        access="rw",
                        reset=reset,  # type: ignore[arg-type]
                    )
                ],
            )
        ]
    )


@pytest.mark.parametrize(
    ("model", "message"),
    [
        (RegisterModel(), "at least one register"),
        (_model(register_name=" "), "Register name"),
        (_model(address=-1), "non-negative integer"),
        (_model(address=True), "non-negative integer"),
        (_model(address=2), "4-byte aligned"),
        (_model(field_name=" "), "name must not be empty"),
        (_model(msb="0"), "bit range must contain integers"),
        (_model(reset=-1), "reset must be a non-negative integer"),
        (_model(reset=True), "reset must be a non-negative integer"),
    ],
)
def test_validate_model_rejects_invalid_direct_models(
    model: RegisterModel, message: str
) -> None:
    with pytest.raises(ModelValidationError, match=message):
        validate_model(model)


@pytest.mark.parametrize("access", sorted(SUPPORTED_ACCESS))
def test_validate_model_accepts_supported_access_definitions(access: str) -> None:
    model = _model()
    model.registers[0].fields[0].access = access

    validate_model(model)


def test_register_decoder_sizing_uses_highest_table_address() -> None:
    model = RegisterModel(
        registers=[
            Register(name="LOW", address=0, fields=[Field("A", 0, 0, "rw", 0)]),
            Register(name="HIGH", address=0x10, fields=[Field("B", 0, 0, "rw", 0)]),
        ]
    )

    assert register_decoder_byte_high(model) == 0x10
    assert register_decoder_addr_width(model) == 5


def test_validate_model_accepts_aligned_address_gaps_and_nonzero_base() -> None:
    model = RegisterModel(
        registers=[
            Register(name="FIRST", address=4, fields=[Field("VALUE", 0, 0, "rw", 0)]),
            Register(name="LAST", address=12, fields=[Field("VALUE", 0, 0, "rw", 0)]),
        ]
    )

    validate_model(model)


def test_register_decoder_sizing_uses_address_range_end() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="MEM",
                address=0x20,
                address_end=0x2F,
                hw_access="external",
                fields=[Field("WINDOW", 31, 0, "rw", 0)],
            )
        ]
    )

    assert register_decoder_byte_high(model) == 0x2F
    assert register_decoder_addr_width(model) == 6


def test_validate_model_rejects_overlapping_address_ranges() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="MEM",
                address=0x00,
                address_end=0x0F,
                hw_access="external",
                fields=[Field("A", 31, 0, "rw", 0)],
            ),
            Register(name="LATE", address=0x08, fields=[Field("B", 0, 0, "rw", 0)]),
        ]
    )
    with pytest.raises(ModelValidationError, match="overlaps"):
        validate_model(model)


def test_register_decoder_byte_high_empty_model() -> None:
    assert register_decoder_byte_high(RegisterModel()) == 0


def test_register_slot_count_single_register_without_range() -> None:
    register = Register(
        name="CTRL",
        address=0x0,
        fields=[Field("EN", 0, 0, "rw", 0)],
    )
    assert register_slot_count(register) == 1


def test_register_range_index_width_single_slot() -> None:
    register = Register(
        name="MEM",
        address=0x20,
        address_end=0x23,
        hw_access="external",
        fields=[Field("WINDOW", 31, 0, "rw", 0)],
    )
    assert register_slot_count(register) == 1
    assert register_range_index_width(register) == 1


def test_validate_model_accepts_last_byte_inclusive_range() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="CONFIG",
                address=0x8000,
                address_end=0x15FFFF,
                hw_access="external",
                fields=[Field("WINDOW", 31, 0, "rw", 0)],
            )
        ]
    )
    validate_model(model)
    assert register_slot_count(model.registers[0]) == 0x56000
    assert register_decoder_byte_high(model) == 0x15FFFF


def test_validate_model_rejects_unsupported_hw_access() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0,
                hw_access="bogus",
                fields=[Field("EN", 0, 0, "rw", 0)],
            )
        ]
    )
    with pytest.raises(ModelValidationError, match="unsupported HW Access"):
        validate_model(model)


@pytest.mark.parametrize(
    ("address", "address_end", "message"),
    [
        (0x20, 0x10, "must be >="),
        (0x20, 0x22, "valid inclusive last byte"),
        (0x20, 0x15FFFE, "valid inclusive last byte"),
    ],
)
def test_validate_model_rejects_invalid_address_ranges(
    address: int, address_end: int, message: str
) -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="MEM",
                address=address,
                address_end=address_end,
                hw_access="external",
                fields=[Field("WINDOW", 31, 0, "rw", 0)],
            )
        ]
    )
    with pytest.raises(ModelValidationError, match=message):
        validate_model(model)


def test_validate_model_rejects_internal_address_range() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="MEM",
                address=0x00,
                address_end=0x0F,
                hw_access="internal",
                fields=[Field("WINDOW", 31, 0, "rw", 0)],
            )
        ]
    )
    with pytest.raises(ModelValidationError, match="HW Access external"):
        validate_model(model)


def _draft(
    *,
    row_number: int = 1,
    register_name: str = "CTRL",
    address: object = 0,
    field_name: str = "ENABLE",
    msb: object = 0,
    lsb: object = 0,
    access: str = "rw",
    reset: object = 0,
    hw_access: str = "internal",
    address_end: object | None = None,
    extra_fields: list[FieldDraft] | None = None,
) -> RegisterDraft:
    fields = [
        FieldDraft(
            row_number=row_number,
            name=field_name,
            msb=msb,  # type: ignore[arg-type]
            lsb=lsb,  # type: ignore[arg-type]
            access=access,
            reset=reset,  # type: ignore[arg-type]
        )
    ]
    if extra_fields:
        fields.extend(extra_fields)
    return RegisterDraft(
        row_number=row_number,
        name=register_name,
        address=address,  # type: ignore[arg-type]
        description="",
        hw_access=hw_access,
        address_end=address_end,  # type: ignore[arg-type]
        fields=fields,
    )


@pytest.mark.parametrize(
    ("drafts", "message"),
    [
        ([], "at least one register"),
        (
            [
                _draft(register_name="CTRL"),
                _draft(row_number=2, register_name="CTRL", address=4),
            ],
            "Duplicate register name",
        ),
        (
            [
                _draft(
                    extra_fields=[
                        FieldDraft(
                            row_number=2,
                            name="ENABLE",
                            msb=1,
                            lsb=1,
                            access="rw",
                            reset=0,
                        )
                    ]
                )
            ],
            "duplicate field name",
        ),
        (
            [
                _draft(
                    msb=3,
                    lsb=0,
                    extra_fields=[
                        FieldDraft(
                            row_number=2,
                            name="HIGH",
                            msb=2,
                            lsb=1,
                            access="rw",
                            reset=0,
                        )
                    ],
                )
            ],
            "overlaps",
        ),
        ([_draft(access="invalid")], "unsupported access"),
    ],
)
def test_collect_register_draft_errors_rejects_invalid_drafts(
    drafts: list[RegisterDraft], message: str
) -> None:
    errors = collect_register_draft_errors(drafts)
    assert errors
    assert message in "\n".join(errors)


def test_collect_register_draft_errors_rejects_register_without_fields() -> None:
    draft = _draft()
    draft.fields = []
    errors = collect_register_draft_errors([draft])
    assert any("at least one field" in error for error in errors)


def test_collect_register_draft_errors_reports_multiple_messages() -> None:
    drafts = [
        _draft(msb=3, lsb=0, reset=0x10),
        _draft(
            row_number=2,
            register_name="OTHER",
            address="bad",  # type: ignore[arg-type]
            msb="x",  # type: ignore[arg-type]
            lsb=0,
            reset=-1,
        ),
    ]
    errors = collect_register_draft_errors(drafts)
    combined = "\n".join(errors)
    assert "reset value" in combined
    assert "address must be" in combined
    assert "bit range must contain integers" in combined


def test_collect_register_draft_errors_skips_overlap_when_bits_not_integers() -> None:
    drafts = [
        RegisterDraft(
            row_number=1,
            name="CTRL",
            address=0,
            description="",
            fields=[
                FieldDraft(
                    row_number=1,
                    name="A",
                    msb="bad",  # type: ignore[arg-type]
                    lsb=0,
                    access="rw",
                    reset=0,
                ),
                FieldDraft(
                    row_number=2,
                    name="B",
                    msb=1,
                    lsb=0,
                    access="rw",
                    reset=0,
                ),
            ],
        )
    ]
    errors = collect_register_draft_errors(drafts)
    assert not any("overlaps" in error for error in errors)


@pytest.mark.parametrize(
    ("msb", "lsb", "reset", "message"),
    [
        (32, 0, 0, "32-bit"),
        (3, 5, 0, "32-bit"),
        (3, 0, 0x10, "does not fit"),
    ],
)
def test_validate_model_rejects_invalid_field_ranges_and_reset(
    msb: int, lsb: int, reset: int, message: str
) -> None:
    with pytest.raises(ModelValidationError, match=message):
        validate_model(_model(msb=msb, lsb=lsb, reset=reset))


def test_validate_model_rejects_register_without_fields() -> None:
    model = RegisterModel(registers=[Register(name="EMPTY", address=0, fields=[])])
    with pytest.raises(ModelValidationError, match="at least one field"):
        validate_model(model)


def test_validate_model_rejects_unsupported_access() -> None:
    model = _model()
    model.registers[0].fields[0].access = "invalid"
    with pytest.raises(ModelValidationError, match="unsupported access"):
        validate_model(model)


def test_validate_model_rejects_duplicate_register_and_field_names() -> None:
    model = RegisterModel(
        registers=[
            Register(name="CTRL", address=0, fields=[Field("A", 0, 0, "rw", 0)]),
            Register(name="CTRL", address=4, fields=[Field("B", 0, 0, "rw", 0)]),
        ]
    )
    with pytest.raises(ModelValidationError, match="Duplicate register name"):
        validate_model(model)

    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0,
                fields=[
                    Field("A", 3, 0, "rw", 0),
                    Field("A", 7, 4, "rw", 0),
                ],
            )
        ]
    )
    with pytest.raises(ModelValidationError, match="duplicate field name"):
        validate_model(model)


def test_validate_model_rejects_overlapping_fields() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="CTRL",
                address=0,
                fields=[
                    Field("LOW", 3, 0, "rw", 0),
                    Field("HIGH", 2, 1, "rw", 0),
                ],
            )
        ]
    )
    with pytest.raises(ModelValidationError, match="overlaps"):
        validate_model(model)


def test_validate_model_rejects_address_range_with_multiple_fields() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="MEM",
                address=0x00,
                address_end=0x0F,
                hw_access="external",
                fields=[
                    Field("LOW", 15, 0, "rw", 0),
                    Field("HIGH", 31, 16, "rw", 0),
                ],
            )
        ]
    )
    with pytest.raises(ModelValidationError, match="exactly one field"):
        validate_model(model)


def test_validate_model_rejects_address_range_with_wrong_bit_span() -> None:
    model = RegisterModel(
        registers=[
            Register(
                name="MEM",
                address=0x00,
                address_end=0x0F,
                hw_access="external",
                fields=[Field("WINDOW", 15, 0, "rw", 0)],
            )
        ]
    )
    with pytest.raises(ModelValidationError, match="must span bits 31:0"):
        validate_model(model)


def test_collect_address_range_errors_returns_empty_without_range_end() -> None:
    from csr_gen.model import _collect_address_range_errors

    draft = _draft(hw_access="internal", address_end=None)
    assert _collect_address_range_errors(draft, "CTRL", "internal") == []


def test_collect_register_draft_errors_rejects_non_integer_address_end() -> None:
    drafts = [
        _draft(
            hw_access="external",
            address_end="bad",  # type: ignore[arg-type]
            msb=31,
            lsb=0,
        )
    ]
    errors = collect_register_draft_errors(drafts)
    assert any("address range end must be" in error for error in errors)


def test_register_range_helpers_for_multi_slot_external_range() -> None:
    register = Register(
        name="MEM",
        address=0x00,
        address_end=0x0F,
        hw_access="external",
        fields=[Field("WINDOW", 31, 0, "rw", 0)],
    )
    assert register_has_address_range(register)
    assert register_is_external(register)
    assert register_slot_count(register) == 4
    assert register_range_index_width(register) == 2
    assert list(register_occupied_offsets(register)) == [0, 4, 8, 12]


def test_register_range_helpers_for_single_address_internal() -> None:
    register = Register(name="CTRL", address=0x10, fields=[Field("EN", 0, 0, "rw", 0)])
    assert not register_has_address_range(register)
    assert not register_is_external(register)
    assert list(register_occupied_offsets(register)) == [0x10]
