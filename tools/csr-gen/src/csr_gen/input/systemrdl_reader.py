"""Read CSR register models from SystemRDL 2.0 addrmaps."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from csr_gen.errors import CsrValidationError
from csr_gen.model import (
    REGISTER_WIDTH,
    FieldDraft,
    RegisterDraft,
    RegisterModel,
    collect_register_draft_errors,
    drafts_to_model,
)
from csr_gen.systemrdl.access import (
    ACCESS_UDP_NAME,
    ADDRESS_END_UDP_NAME,
    access_from_rdl_properties,
)

try:
    from systemrdl import RDLCompiler, RDLWalker, RDLListener
    from systemrdl.component import Field as RdlFieldComponent
    from systemrdl.component import Reg as RdlRegComponent
    from systemrdl.node import AddrmapNode, FieldNode, RegNode, RegfileNode
    from systemrdl.udp import UDPDefinition
    from systemrdl.walker import WalkerAction
except ImportError:  # pragma: no cover - exercised via import guard tests
    RDLCompiler = None  # type: ignore[misc, assignment]
    RDLWalker = None  # type: ignore[misc, assignment]
    RDLListener = object  # type: ignore[misc, assignment]
    RdlFieldComponent = Reg = Field = object  # type: ignore[misc, assignment]
    RdlRegComponent = object  # type: ignore[misc, assignment]
    AddrmapNode = RegNode = FieldNode = RegfileNode = object  # type: ignore[misc, assignment]
    UDPDefinition = object  # type: ignore[misc, assignment]
    WalkerAction = object  # type: ignore[misc, assignment]


class SystemRdlParseError(CsrValidationError):
    """Raised when a SystemRDL file cannot be parsed or imported."""


@dataclass
class SystemRdlRegisterSpec:
    """A register model parsed from a SystemRDL addrmap."""

    model: RegisterModel
    section_heading: str
    addrmap_name: str
    heading_level: int = 2


class _AddressEndUDP(UDPDefinition):
    name = ADDRESS_END_UDP_NAME
    valid_components = {RdlRegComponent}
    valid_type = int


class _AccessUDP(UDPDefinition):
    name = ACCESS_UDP_NAME
    valid_components = {RdlFieldComponent}
    valid_type = str


def load_systemrdl_file(
    path: Path,
    *,
    addrmap_instance: str | None = None,
) -> SystemRdlRegisterSpec:
    """Read and validate CSR registers from a SystemRDL file."""
    return load_systemrdl(
        path.read_text(encoding="utf-8"),
        path.name,
        addrmap_instance=addrmap_instance,
    )


def load_systemrdl(
    text: str,
    source_name: str = "<memory>",
    *,
    addrmap_instance: str | None = None,
) -> SystemRdlRegisterSpec:
    """Read and validate CSR registers from a SystemRDL string."""
    _require_compiler()
    compiler = RDLCompiler()
    compiler.register_udp(_AddressEndUDP, soft=True)
    compiler.register_udp(_AccessUDP, soft=True)
    temp_path = _write_temp_rdl(source_name, text)
    try:
        compiler.compile_file(temp_path)
        root = compiler.elaborate()
    except Exception as error:
        raise SystemRdlParseError([f"{source_name}: {error}"]) from error
    finally:
        _remove_temp_rdl(temp_path)

    addrmaps = [node for node in root.descendants() if isinstance(node, AddrmapNode)]
    top_addrmaps = [node for node in addrmaps if node.parent is root]
    if len(top_addrmaps) != 1:
        raise SystemRdlParseError(
            [
                f"{source_name}: expected exactly one top-level addrmap, "
                f"found {len(top_addrmaps)}."
            ]
        )
    top_addrmap = top_addrmaps[0]
    walk_root = _resolve_import_root(
        top_addrmap,
        addrmap_instance,
        source_name,
    )
    listener = _RegisterCollector(source_name)
    RDLWalker(unroll=True).walk(walk_root, listener)
    if listener.errors:
        raise SystemRdlParseError(listener.errors)

    drafts = listener.drafts
    _disambiguate_register_names(drafts, listener.name_prefixes)
    errors = collect_register_draft_errors(drafts)
    if errors:
        raise SystemRdlParseError(errors)

    section_heading = _section_heading(walk_root)
    return SystemRdlRegisterSpec(
        model=drafts_to_model(drafts),
        section_heading=section_heading,
        addrmap_name=walk_root.inst_name,
    )


def list_systemrdl_addrmap_instances(
    text: str,
    source_name: str = "<memory>",
) -> list[str]:
    """Return nested addrmap instance names when import requires a selector."""
    _require_compiler()
    compiler = RDLCompiler()
    compiler.register_udp(_AddressEndUDP, soft=True)
    compiler.register_udp(_AccessUDP, soft=True)
    temp_path = _write_temp_rdl(source_name, text)
    try:
        compiler.compile_file(temp_path)
        root = compiler.elaborate()
    except Exception as error:
        raise SystemRdlParseError([f"{source_name}: {error}"]) from error
    finally:
        _remove_temp_rdl(temp_path)

    addrmaps = [node for node in root.descendants() if isinstance(node, AddrmapNode)]
    top_addrmaps = [node for node in addrmaps if node.parent is root]
    if len(top_addrmaps) != 1:
        raise SystemRdlParseError(
            [
                f"{source_name}: expected exactly one top-level addrmap, "
                f"found {len(top_addrmaps)}."
            ]
        )
    nested = _nested_addrmap_instances(top_addrmaps[0])
    if len(nested) <= 1:
        return []
    return [node.inst_name for node in nested]


def list_systemrdl_addrmap_instances_file(path: Path) -> list[str]:
    """Return nested addrmap instance names when import requires a selector."""
    return list_systemrdl_addrmap_instances(
        path.read_text(encoding="utf-8"),
        path.name,
    )


class _RegisterCollector(RDLListener):
    def __init__(self, source_name: str) -> None:
        self._source_name = source_name
        self.drafts: list[RegisterDraft] = []
        self.name_prefixes: list[str] = []
        self.errors: list[str] = []
        self._row_number = 0
        self._field_row = 0
        self._regfile_prefix_stack: list[str] = []

    def enter_Regfile(self, node: RegfileNode) -> None:
        self._regfile_prefix_stack.append(node.inst_name)

    def exit_Regfile(self, node: RegfileNode) -> None:
        if self._regfile_prefix_stack:
            self._regfile_prefix_stack.pop()

    def enter_Mem(self, node: object) -> WalkerAction:
        inst_name = getattr(node, "inst_name", "<unnamed>")
        self.errors.append(
            f"{self._source_name}: memory component {inst_name!r} is not supported."
        )
        return WalkerAction.SkipDescendants

    def enter_Signal(self, node: object) -> WalkerAction:
        inst_name = getattr(node, "inst_name", "<unnamed>")
        self.errors.append(
            f"{self._source_name}: signal component {inst_name!r} is not supported."
        )
        return WalkerAction.SkipDescendants

    def enter_Reg(self, node: RegNode) -> None:
        if node.current_idx is not None and node.current_idx != [0]:
            return

        if not isinstance(node.parent, (AddrmapNode, RegfileNode)):
            self.errors.append(
                f"{self._source_name}: register {node.inst_name!r} has an "
                "unsupported parent component."
            )
            return

        try:
            regwidth = int(node.get_property("regwidth"))
        except LookupError:
            regwidth = REGISTER_WIDTH
        if regwidth != REGISTER_WIDTH:
            self.errors.append(
                f"{self._source_name}: register {node.inst_name!r} requires "
                f"regwidth={REGISTER_WIDTH}, found {regwidth}."
            )
            return

        self._row_number += 1
        self._field_row = 0
        address = node.absolute_address
        hw_access = "external" if node.external else "internal"
        address_end = _register_address_end(node)
        fields = [self._field_draft(field) for field in _field_nodes(node)]
        if not fields:
            self.errors.append(
                f"{self._source_name}: register {node.inst_name!r} must contain "
                "at least one field."
            )
            return
        description = _optional_property(node, "desc") or node.inst_name
        draft = RegisterDraft(
            row_number=self._row_number,
            name=node.inst_name,
            address=address,
            description=str(description),
            hw_access=hw_access,
            address_end=address_end,
            fields=fields,
        )
        if address_end is not None and address_end < address:
            self.errors.append(
                f"{self._source_name}: register {node.inst_name!r} has "
                f"{ADDRESS_END_UDP_NAME} {address_end:#x} before its base address "
                f"{address:#x}."
            )
            return
        if address_end is not None and not _aligned_range(address, address_end):
            self.errors.append(
                f"{self._source_name}: register {node.inst_name!r} address range "
                f"{address:#x}-{address_end:#x} is not 4-byte aligned."
            )
            return
        self.drafts.append(draft)
        self.name_prefixes.append(self._current_regfile_prefix())

    def _current_regfile_prefix(self) -> str:
        if not self._regfile_prefix_stack:
            return ""
        return "_".join(self._regfile_prefix_stack) + "_"

    def _field_draft(self, node: FieldNode) -> FieldDraft:
        self._field_row += 1
        access = access_from_rdl_properties(
            csr_gen_access=_optional_property(node, ACCESS_UDP_NAME),
            sw=node.get_property("sw"),
            onread=_optional_property(node, "onread"),
            onwrite=_optional_property(node, "onwrite"),
        )
        description = _optional_property(node, "desc") or node.inst_name
        reset_raw = _optional_property(node, "reset")
        reset = 0 if reset_raw is None else int(reset_raw)
        return FieldDraft(
            row_number=self._field_row,
            name=node.inst_name,
            msb=node.msb,
            lsb=node.lsb,
            access=access,
            reset=reset,
            description=str(description),
        )


def _nested_addrmap_instances(top: AddrmapNode) -> list[AddrmapNode]:
    return [child for child in top.children() if isinstance(child, AddrmapNode)]


def _resolve_import_root(
    top: AddrmapNode,
    addrmap_instance: str | None,
    source_name: str,
) -> AddrmapNode:
    nested = _nested_addrmap_instances(top)
    if len(nested) > 1:
        if addrmap_instance is None:
            names = ", ".join(node.inst_name for node in nested)
            raise SystemRdlParseError(
                [
                    f"{source_name}: multiple nested addrmap instances; "
                    f"use --systemrdl-addrmap to select one. Instances: {names}."
                ]
            )
        matched = [node for node in nested if node.inst_name == addrmap_instance]
        if not matched:
            raise SystemRdlParseError(
                [
                    f"{source_name}: no nested addrmap instance named "
                    f"{addrmap_instance!r}."
                ]
            )
        return matched[0]
    if addrmap_instance is not None:
        if addrmap_instance == top.inst_name:
            return top
        if len(nested) == 1 and nested[0].inst_name == addrmap_instance:
            return nested[0]
        raise SystemRdlParseError(
            [
                f"{source_name}: no nested addrmap instance named "
                f"{addrmap_instance!r}."
            ]
        )
    return top


def _disambiguate_register_names(
    drafts: list[RegisterDraft],
    prefixes: list[str],
) -> None:
    if len(prefixes) != len(drafts):
        return
    name_counts = Counter(draft.name for draft in drafts)
    for draft, prefix in zip(drafts, prefixes, strict=True):
        if name_counts[draft.name] > 1 and prefix:
            draft.name = f"{prefix}{draft.name}"


def _field_nodes(register: RegNode) -> list[FieldNode]:
    return [node for node in register.descendants() if isinstance(node, FieldNode)]


def _register_address_end(node: RegNode) -> int | None:
    dimensions = node.array_dimensions
    if dimensions and dimensions[0] > 1:
        count = dimensions[0]
        stride = int(node.get_property("regwidth")) // 8
        return node.absolute_address + count * stride - 1
    legacy = _optional_property(node, ADDRESS_END_UDP_NAME)
    if legacy is None:
        return None
    address_end = int(legacy)
    # Legacy csr_gen_address_end stored the last word address (4-byte aligned).
    # Last-byte ends are always 3 mod 4; convert aligned legacy values.
    if address_end % 4 == 0:
        return address_end + 3
    return address_end


def _section_heading(addrmap: AddrmapNode) -> str:
    description = _optional_property(addrmap, "desc")
    if description:
        return str(description)
    return addrmap.inst_name


def _optional_property(node: object, name: str) -> object | None:
    try:
        return node.get_property(name)  # type: ignore[union-attr]
    except LookupError:
        return None


def _aligned_range(address: int, address_end: int) -> bool:
    if address % 4:
        return False
    if address_end < address:
        return False
    byte_count = address_end - address + 1
    return byte_count % 4 == 0


def _require_compiler() -> None:
    if RDLCompiler is None:
        raise SystemRdlParseError(
            [
                "SystemRDL import requires the optional systemrdl-compiler package. "
                "Install it with: pip install systemrdl-compiler"
            ]
        )


def _write_temp_rdl(source_name: str, text: str) -> str:
    import tempfile

    handle = tempfile.NamedTemporaryFile(
        "w",
        suffix=".rdl",
        prefix="csr_gen_",
        delete=False,
        encoding="utf-8",
    )
    handle.write(text)
    handle.close()
    return handle.name


def _remove_temp_rdl(path: str) -> None:
    import os

    os.unlink(path)
