"""Intermediate CSR register model and legality validation."""

from dataclasses import dataclass, field

from csr_gen.errors import ModelValidationError
from csr_gen.names import csr_identifier_error

REGISTER_WIDTH = 32
REGISTER_BYTES = REGISTER_WIDTH // 8

DEFAULT_HW_ACCESS = "internal"

# Access keywords accepted in Markdown tables. Semantics align with SystemRDL
# field sw access plus onread/onwrite behavior (see docs/DEVELOPMENT.md).
SUPPORTED_ACCESS = frozenset(
    {
        "none",
        "ro",
        "rc",
        "rw",
        "r0w1c",
        "rw1s",
        "rw1c",
        "rw0c",
        "wo",
    }
)

SUPPORTED_HW_ACCESS = frozenset({"internal", "external"})


@dataclass
class Field:
    """A field within a CSR register."""

    name: str
    msb: int
    lsb: int
    access: str
    reset: int
    description: str = ""

    def __post_init__(self) -> None:
        self.name = self.name.strip().upper()
        self.access = self.access.strip().lower()
        self.description = self.description.strip()


@dataclass
class Register:
    """A 32-bit CSR register."""

    name: str
    address: int
    description: str = ""
    fields: list[Field] = field(default_factory=list)
    hw_access: str = DEFAULT_HW_ACCESS
    address_end: int | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip().upper()
        self.description = self.description.strip()
        self.hw_access = self.hw_access.strip().lower()


@dataclass
class RegisterModel:
    """Normalized register model shared by all readers and serializers."""

    registers: list[Register] = field(default_factory=list)


def register_address_end(register: Register) -> int:
    """Return the inclusive last byte offset occupied by a register."""
    if register.address_end is not None:
        return register.address_end
    return register.address


def register_has_address_range(register: Register) -> bool:
    """Return whether the register occupies a span of byte offsets."""
    return register.address_end is not None


def register_slot_count(register: Register) -> int:
    """Return the number of 32-bit slots in a register map entry."""
    if not register_has_address_range(register):
        return 1
    byte_count = register_address_end(register) - register.address + 1
    return byte_count // REGISTER_BYTES


def register_range_index_width(register: Register) -> int:
    """Return the sub-address index width for a ranged external register."""
    slot_count = register_slot_count(register)
    if slot_count <= 1:
        return 1
    return max(1, (slot_count - 1).bit_length())


def register_is_external(register: Register) -> bool:
    """Return whether RTL delegates the register to external hardware."""
    return register.hw_access == "external"


def register_occupied_offsets(register: Register) -> range:
    """Return byte offsets claimed by a register in the CSR map."""
    return range(
        register.address,
        register_address_end(register) + 1,
        REGISTER_BYTES,
    )


def register_decoder_byte_high(model: RegisterModel) -> int:
    """Return the highest byte offset used by any register in the block."""
    if not model.registers:
        return 0
    return max(register_address_end(register) for register in model.registers)


def register_decoder_addr_width(model: RegisterModel) -> int:
    """Return the address bit width for a byte-offset decoder through the map high."""
    high = register_decoder_byte_high(model)
    return max(1, (high + REGISTER_BYTES).bit_length())


@dataclass
class FieldDraft:
    """Field parsed from a Markdown table row before model assembly."""

    row_number: int
    name: str
    msb: int
    lsb: int
    access: str
    reset: int
    description: str = ""


@dataclass
class RegisterDraft:
    """Register parsed from Markdown table rows before model assembly."""

    row_number: int
    name: str
    address: int
    description: str
    fields: list[FieldDraft] = field(default_factory=list)
    hw_access: str = DEFAULT_HW_ACCESS
    address_end: int | None = None


def row_error(row_number: int, message: str) -> str:
    """Format a CSR table row validation message."""
    return f"CSR table row {row_number}: {message}"


def drafts_to_model(drafts: list[RegisterDraft]) -> RegisterModel:
    """Convert validated register drafts into a register model."""
    registers = []
    for draft in drafts:
        register = Register(
            name=draft.name,
            address=draft.address,
            description=draft.description,
            hw_access=draft.hw_access,
            address_end=draft.address_end,
        )
        for field_draft in draft.fields:
            register.fields.append(
                Field(
                    name=field_draft.name,
                    msb=field_draft.msb,
                    lsb=field_draft.lsb,
                    access=field_draft.access,
                    reset=field_draft.reset,
                    description=field_draft.description,
                )
            )
        registers.append(register)
    return RegisterModel(registers=registers)


def collect_register_draft_errors(
    drafts: list[RegisterDraft],
    *,
    allow_empty_fields: bool = False,
) -> list[str]:
    """Return all legality errors for parsed Markdown register drafts."""
    errors: list[str] = []
    if not drafts:
        errors.append("Register model must contain at least one register.")
        return errors

    register_names: dict[str, int] = {}
    occupied_offsets: dict[int, int] = {}

    for draft in drafts:
        errors.extend(
            _collect_register_draft_errors(
                draft,
                allow_empty_fields=allow_empty_fields,
            )
        )
        normalized_register_name = draft.name.strip().upper()
        if normalized_register_name in register_names:
            errors.append(
                row_error(
                    draft.row_number,
                    f"Duplicate register name {normalized_register_name} "
                    f"(also on row {register_names[normalized_register_name]}).",
                )
            )
        register_names[normalized_register_name] = draft.row_number

        if not _is_integer(draft.address):
            continue
        if draft.address_end is not None and not _is_integer(draft.address_end):
            continue
        for offset in register_occupied_offsets(
            Register(
                name=draft.name,
                address=draft.address,
                address_end=draft.address_end,
            )
        ):
            if offset in occupied_offsets:
                errors.append(
                    row_error(
                        draft.row_number,
                        f"Register address {offset:#x} overlaps "
                        f"(also on row {occupied_offsets[offset]}).",
                    )
                )
            else:
                occupied_offsets[offset] = draft.row_number

    return errors


def _collect_register_draft_errors(
    draft: RegisterDraft,
    *,
    allow_empty_fields: bool = False,
) -> list[str]:
    errors: list[str] = []
    register_name = draft.name.strip().upper()
    if not register_name:
        errors.append(row_error(draft.row_number, "Register name must not be empty."))
    else:
        name_error = csr_identifier_error(draft.name, kind="Register")
        if name_error is not None:
            errors.append(row_error(draft.row_number, name_error))
    if not _is_integer(draft.address):
        errors.append(
            row_error(
                draft.row_number,
                f"Register {register_name or '<empty>'} address must be "
                "a non-negative integer.",
            )
        )
    elif draft.address < 0:
        errors.append(
            row_error(
                draft.row_number,
                f"Register {register_name or '<empty>'} address must be "
                "a non-negative integer.",
            )
        )
    elif draft.address % REGISTER_BYTES:
        errors.append(
            row_error(
                draft.row_number,
                f"Register {register_name} address {draft.address:#x} must be "
                f"{REGISTER_BYTES}-byte aligned.",
            )
        )

    hw_access = draft.hw_access.strip().lower()
    if hw_access not in SUPPORTED_HW_ACCESS:
        errors.append(
            row_error(
                draft.row_number,
                f"Register {register_name} has unsupported HW Access: "
                f"{draft.hw_access}.",
            )
        )

    if draft.address_end is not None:
        errors.extend(_collect_address_range_errors(draft, register_name, hw_access))

    if not draft.fields and not allow_empty_fields:
        errors.append(
            row_error(
                draft.row_number,
                f"Register {register_name or '<empty>'} must contain at least "
                "one field.",
            )
        )

    field_names: dict[str, int] = {}
    parsed_fields: list[FieldDraft] = []
    for field_draft in draft.fields:
        errors.extend(_collect_field_draft_errors(register_name, field_draft))
        normalized_name = field_draft.name.strip().upper()
        if normalized_name in field_names:
            errors.append(
                row_error(
                    field_draft.row_number,
                    f"Register {register_name} has duplicate field name "
                    f"{normalized_name} (also on row {field_names[normalized_name]}).",
                )
            )
        if _is_integer(field_draft.msb) and _is_integer(field_draft.lsb):
            field_bits = set(range(field_draft.lsb, field_draft.msb + 1))
        else:
            field_bits = set()
        for other_field in parsed_fields:
            if not _is_integer(other_field.msb) or not _is_integer(other_field.lsb):
                continue
            if field_bits.intersection(range(other_field.lsb, other_field.msb + 1)):
                errors.append(
                    row_error(
                        field_draft.row_number,
                        f"Register {register_name} field {normalized_name} overlaps "
                        f"field {other_field.name.strip().upper()} on row "
                        f"{other_field.row_number}.",
                    )
                )
                break
        field_names[normalized_name] = field_draft.row_number
        parsed_fields.append(field_draft)

    return errors


def _collect_address_range_errors(
    draft: RegisterDraft, register_name: str, hw_access: str
) -> list[str]:
    errors: list[str] = []
    address_end = draft.address_end
    if address_end is None:
        return errors
    if hw_access != "external":
        errors.append(
            row_error(
                draft.row_number,
                f"Register {register_name} address range requires "
                "HW Access external.",
            )
        )
    if not _is_integer(address_end):
        errors.append(
            row_error(
                draft.row_number,
                f"Register {register_name} address range end must be "
                "a non-negative integer.",
            )
        )
        return errors
    if address_end < draft.address:
        errors.append(
            row_error(
                draft.row_number,
                f"Register {register_name} address range end {address_end:#x} "
                f"must be >= start {draft.address:#x}.",
            )
        )
        return errors
    byte_count = address_end - draft.address + 1
    if byte_count % REGISTER_BYTES:
        lower = draft.address + (byte_count // REGISTER_BYTES) * REGISTER_BYTES - 1
        if lower < draft.address:
            lower = draft.address + REGISTER_BYTES - 1
        upper = lower + REGISTER_BYTES
        errors.append(
            row_error(
                draft.row_number,
                f"Register {register_name} address range end {address_end:#x} is not "
                f"a valid inclusive last byte (byte count must be a multiple of "
                f"{REGISTER_BYTES}); use {lower:#x} or {upper:#x}.",
            )
        )
    if len(draft.fields) != 1:
        errors.append(
            row_error(
                draft.row_number,
                f"Register {register_name} address range requires exactly one field.",
            )
        )
    elif _is_integer(draft.fields[0].msb) and _is_integer(draft.fields[0].lsb):
        field = draft.fields[0]
        if field.msb != REGISTER_WIDTH - 1 or field.lsb != 0:
            errors.append(
                row_error(
                    draft.row_number,
                    f"Register {register_name} address range field "
                    f"{field.name.strip().upper()} must span bits "
                    f"{REGISTER_WIDTH - 1}:0.",
                )
            )
    return errors


def _collect_field_draft_errors(
    register_name: str, field_draft: FieldDraft
) -> list[str]:
    errors: list[str] = []
    field_name = field_draft.name.strip().upper() or "<empty>"
    if not field_draft.name.strip():
        errors.append(
            row_error(field_draft.row_number, "Field name must not be empty.")
        )
    else:
        name_error = csr_identifier_error(field_draft.name, kind="Field")
        if name_error is not None:
            errors.append(row_error(field_draft.row_number, name_error))
    if not _is_integer(field_draft.msb) or not _is_integer(field_draft.lsb):
        errors.append(
            row_error(
                field_draft.row_number,
                f"Register {register_name} field {field_name} bit range must contain "
                "integers.",
            )
        )
    elif (
        field_draft.lsb < 0
        or field_draft.msb < field_draft.lsb
        or field_draft.msb >= REGISTER_WIDTH
    ):
        errors.append(
            row_error(
                field_draft.row_number,
                f"Register {register_name} field {field_name} bit range must fit "
                f"within a {REGISTER_WIDTH}-bit register.",
            )
        )
    access = field_draft.access.strip().lower()
    if access not in SUPPORTED_ACCESS:
        errors.append(
            row_error(
                field_draft.row_number,
                f"Register {register_name} field {field_name} has unsupported "
                f"access: {field_draft.access}.",
            )
        )
    if not _is_integer(field_draft.reset) or field_draft.reset < 0:
        errors.append(
            row_error(
                field_draft.row_number,
                f"Register {register_name} field {field_name} reset must be a "
                "non-negative integer.",
            )
        )
    elif (
        _is_integer(field_draft.msb)
        and _is_integer(field_draft.lsb)
        and field_draft.msb >= field_draft.lsb
    ):
        width = field_draft.msb - field_draft.lsb + 1
        if field_draft.reset >= 1 << width:
            errors.append(
                row_error(
                    field_draft.row_number,
                    f"Register {register_name} field {field_name} reset value "
                    f"{field_draft.reset:#x} does not fit within {width} bits.",
                )
            )
    return errors


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def collect_model_errors(model: RegisterModel) -> list[str]:
    """Return all legality errors for an assembled register model."""
    drafts = [
        RegisterDraft(
            row_number=index,
            name=register.name,
            address=register.address,
            description=register.description,
            hw_access=register.hw_access,
            address_end=register.address_end,
            fields=[
                FieldDraft(
                    row_number=field_index,
                    name=register_field.name,
                    msb=register_field.msb,
                    lsb=register_field.lsb,
                    access=register_field.access,
                    reset=register_field.reset,
                    description=register_field.description,
                )
                for field_index, register_field in enumerate(register.fields, start=1)
            ],
        )
        for index, register in enumerate(model.registers, start=1)
    ]
    return collect_register_draft_errors(drafts)


def validate_model(model: RegisterModel) -> None:
    """Raise when a register model is illegal."""
    errors = collect_model_errors(model)
    if errors:
        raise ModelValidationError(errors)
