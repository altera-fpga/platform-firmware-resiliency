import pytest

from csr_gen.input import systemrdl_reader as reader
from csr_gen.input.systemrdl_reader import (
    SystemRdlParseError,
    _RegisterCollector,
    _aligned_range,
    _disambiguate_register_names,
    _resolve_import_root,
    load_systemrdl,
)
from csr_gen.model import FieldDraft, RegisterDraft


def test_aligned_range() -> None:
    assert _aligned_range(0x0, 0xF) is True
    assert _aligned_range(0x0, 0xC) is False
    assert _aligned_range(0x1, 0x4) is False
    assert _aligned_range(0x0, 0x5) is False
    assert _aligned_range(0x8, 0x4) is False


def test_register_collector_rejects_unsupported_register_parent(monkeypatch) -> None:
    class FakeAddrmap:
        pass

    class FakeRegfile:
        pass

    monkeypatch.setattr(reader, "AddrmapNode", FakeAddrmap)
    monkeypatch.setattr(reader, "RegfileNode", FakeRegfile)
    collector = _RegisterCollector("test.rdl")

    class FakeParent:
        pass

    class FakeRegNode:
        inst_name = "INNER"
        parent = FakeParent()
        absolute_address = 0
        external = False
        current_idx = None
        array_dimensions = None

        def get_property(self, name: str):
            if name == "regwidth":
                return 32
            raise LookupError(name)

    collector.enter_Reg(FakeRegNode())  # type: ignore[arg-type]
    assert collector.errors
    assert "unsupported parent component" in collector.errors[0]


def test_register_collector_accepts_regfile_parent(monkeypatch) -> None:
    class FakeAddrmap:
        pass

    class FakeRegfile:
        pass

    monkeypatch.setattr(reader, "AddrmapNode", FakeAddrmap)
    monkeypatch.setattr(reader, "RegfileNode", FakeRegfile)
    monkeypatch.setattr(
        reader,
        "_field_nodes",
        lambda _register: [object()],
    )
    monkeypatch.setattr(
        _RegisterCollector,
        "_field_draft",
        lambda self, _node: FieldDraft(
            row_number=1,
            name="A",
            msb=0,
            lsb=0,
            access="rw",
            reset=0,
            description="",
        ),
    )
    collector = _RegisterCollector("test.rdl")
    collector._regfile_prefix_stack.append("bank_inst")

    class FakeRegNode:
        inst_name = "INNER"
        parent = FakeRegfile()
        absolute_address = 0x100
        external = False
        current_idx = None
        array_dimensions = None

        def get_property(self, name: str):
            if name == "regwidth":
                return 32
            if name == "desc":
                return "Inner"
            raise LookupError(name)

    collector.enter_Reg(FakeRegNode())  # type: ignore[arg-type]
    assert not collector.errors
    assert collector.drafts
    assert collector.drafts[0].address == 0x100
    assert collector.name_prefixes == ["bank_inst_"]


def test_register_collector_rejects_register_without_fields(monkeypatch) -> None:
    class FakeAddrmap:
        pass

    monkeypatch.setattr(reader, "AddrmapNode", FakeAddrmap)
    collector = _RegisterCollector("test.rdl")

    class FakeRegNode:
        inst_name = "EMPTY"
        parent = FakeAddrmap()
        absolute_address = 0
        external = False
        current_idx = None
        array_dimensions = None

        def get_property(self, name: str):
            if name == "regwidth":
                return 32
            if name == "desc":
                return None
            raise LookupError(name)

    monkeypatch.setattr(
        reader,
        "_field_nodes",
        lambda _register: [],
    )
    collector.enter_Reg(FakeRegNode())  # type: ignore[arg-type]
    assert collector.errors
    assert "at least one field" in collector.errors[0]


def test_register_collector_rejects_bad_address_end(monkeypatch) -> None:
    class FakeAddrmap:
        pass

    monkeypatch.setattr(reader, "AddrmapNode", FakeAddrmap)
    monkeypatch.setattr(
        reader,
        "_field_nodes",
        lambda _register: [object()],
    )
    monkeypatch.setattr(
        _RegisterCollector,
        "_field_draft",
        lambda self, _node: FieldDraft(
            row_number=1,
            name="A",
            msb=0,
            lsb=0,
            access="rw",
            reset=0,
            description="",
        ),
    )
    collector = _RegisterCollector("test.rdl")

    class FakeRegNode:
        inst_name = "BAD"
        parent = FakeAddrmap()
        absolute_address = 0x10
        external = False
        current_idx = None
        array_dimensions = None

        def get_property(self, name: str):
            if name == reader.ADDRESS_END_UDP_NAME:
                return 0x8
            if name == "regwidth":
                return 32
            if name == "desc":
                return "bad"
            raise LookupError(name)

    collector.enter_Reg(FakeRegNode())  # type: ignore[arg-type]
    assert any("before its base address" in error for error in collector.errors)


def test_register_collector_uses_default_regwidth_when_property_missing(
    monkeypatch,
) -> None:
    class FakeAddrmap:
        pass

    monkeypatch.setattr(reader, "AddrmapNode", FakeAddrmap)
    monkeypatch.setattr(
        reader,
        "_field_nodes",
        lambda _register: [object()],
    )
    monkeypatch.setattr(
        _RegisterCollector,
        "_field_draft",
        lambda self, _node: FieldDraft(
            row_number=1,
            name="A",
            msb=0,
            lsb=0,
            access="rw",
            reset=0,
            description="",
        ),
    )
    collector = _RegisterCollector("test.rdl")

    class FakeRegNode:
        inst_name = "CTRL"
        parent = FakeAddrmap()
        absolute_address = 0
        external = False
        current_idx = None
        array_dimensions = None

        def get_property(self, name: str):
            if name == "desc":
                return "Control"
            raise LookupError(name)

    collector.enter_Reg(FakeRegNode())  # type: ignore[arg-type]
    assert collector.drafts
    assert collector.drafts[0].name == "CTRL"


def test_load_systemrdl_rejects_model_validation_errors() -> None:
    rdl = """
property csr_gen_access { type = string; component = field; };
addrmap top {
    desc = "CSR";
    reg {
        regwidth = 32;
        field { sw = rw; csr_gen_access = "rw"; } a[0:0] = 0;
    } BAD @ 0x1;
};
"""
    with pytest.raises(SystemRdlParseError, match="4-byte aligned"):
        load_systemrdl(rdl, "unaligned.rdl")


def test_load_systemrdl_raises_collector_errors(monkeypatch) -> None:
    class FakeAddrmapNode:
        inst_name = "top"

        def get_property(self, name: str):
            if name == "desc":
                return "CSR"
            raise LookupError(name)

        def children(self):
            return []

    class FakeCompiler:
        def register_udp(self, *_args, **_kwargs) -> None:
            return None

        def compile_file(self, _path: str):
            return None

        def elaborate(self):
            class Root:
                def descendants(self):
                    node = FakeAddrmapNode()
                    node.parent = self
                    return [node]

            return Root()

    class FakeWalker:
        def __init__(self, unroll: bool = False) -> None:
            self.unroll = unroll

        def walk(self, _node, listener) -> None:
            listener.errors.append("collector failed")

    monkeypatch.setattr(reader, "RDLCompiler", FakeCompiler)
    monkeypatch.setattr(reader, "AddrmapNode", FakeAddrmapNode)
    monkeypatch.setattr(
        reader,
        "RDLWalker",
        FakeWalker,
    )

    with pytest.raises(SystemRdlParseError, match="collector failed"):
        load_systemrdl("addrmap top {};", "collector.rdl")


def test_load_systemrdl_rejects_multiple_top_level_addrmaps(monkeypatch) -> None:
    class FakeAddrmapNode:
        pass

    root = object()
    first = FakeAddrmapNode()
    first.parent = root
    second = FakeAddrmapNode()
    second.parent = root

    class FakeCompiler:
        def register_udp(self, *_args, **_kwargs) -> None:
            return None

        def compile_file(self, _path: str):
            return None

        def elaborate(self):
            return type(
                "Root",
                (),
                {"descendants": lambda self: [first, second]},
            )()

    monkeypatch.setattr(reader, "RDLCompiler", FakeCompiler)
    monkeypatch.setattr(reader, "AddrmapNode", FakeAddrmapNode)
    monkeypatch.setattr(
        reader,
        "RDLWalker",
        lambda: type(
            "Walker",
            (),
            {"walk": lambda self, _node, _listener: None},
        )(),
    )

    with pytest.raises(SystemRdlParseError, match="exactly one top-level addrmap"):
        load_systemrdl("addrmap top {};", "multi.rdl")


def test_disambiguate_register_names_skips_mismatched_prefix_length() -> None:
    drafts = [
        RegisterDraft(
            row_number=1,
            name="STATUS",
            address=0,
            description="",
            fields=[],
        ),
        RegisterDraft(
            row_number=2,
            name="STATUS",
            address=0x100,
            description="",
            fields=[],
        ),
    ]
    _disambiguate_register_names(drafts, ["bank_a_"])
    assert drafts[0].name == "STATUS"
    assert drafts[1].name == "STATUS"


def test_resolve_import_root_selects_top_by_instance_name(monkeypatch) -> None:
    class FakeAddrmap:
        pass

    monkeypatch.setattr(reader, "AddrmapNode", FakeAddrmap)

    nested = FakeAddrmap()
    nested.inst_name = "child_inst"
    top = FakeAddrmap()
    top.inst_name = "top_device"
    top.children = lambda: [nested]

    selected = _resolve_import_root(top, "top_device", "pick.rdl")  # type: ignore[arg-type]
    assert selected is top


def test_resolve_import_root_selects_single_nested_by_instance_name(
    monkeypatch,
) -> None:
    class FakeAddrmap:
        pass

    monkeypatch.setattr(reader, "AddrmapNode", FakeAddrmap)

    nested = FakeAddrmap()
    nested.inst_name = "child_inst"
    top = FakeAddrmap()
    top.inst_name = "top_device"
    top.children = lambda: [nested]

    selected = _resolve_import_root(top, "child_inst", "pick.rdl")  # type: ignore[arg-type]
    assert selected is nested


def test_resolve_import_root_rejects_unknown_instance_on_flat_top(monkeypatch) -> None:
    class FakeAddrmap:
        pass

    monkeypatch.setattr(reader, "AddrmapNode", FakeAddrmap)

    top = FakeAddrmap()
    top.inst_name = "top_device"
    top.children = lambda: []

    with pytest.raises(SystemRdlParseError, match="no nested addrmap instance"):
        _resolve_import_root(top, "missing_inst", "flat.rdl")  # type: ignore[arg-type]
