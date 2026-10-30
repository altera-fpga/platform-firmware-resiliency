"""Tests for csr-gen-gui command-line handling."""

from __future__ import annotations

from pathlib import Path

from csr_gen_gui.main import build_argument_parser, parse_args


def test_parse_args_accepts_optional_file() -> None:
    args, unknown = parse_args(["specs/golden/example-device/regs.md"])
    assert args.file == Path("specs/golden/example-device/regs.md")
    assert unknown == []


def test_parse_args_with_no_file() -> None:
    args, unknown = parse_args([])
    assert args.file is None
    assert unknown == []


def test_parse_args_leaves_qt_flags_for_application() -> None:
    args, unknown = parse_args(["regs.md", "-style", "Fusion"])
    assert args.file == Path("regs.md")
    assert unknown == ["-style", "Fusion"]


def test_parse_args_qt_style_without_file() -> None:
    args, unknown = parse_args(["-style", "Fusion"])
    assert args.file is None
    assert unknown == ["-style", "Fusion"]


def test_parse_args_qt_style_before_file() -> None:
    args, unknown = parse_args(["-style", "Fusion", "regs.md"])
    assert args.file == Path("regs.md")
    assert unknown == ["-style", "Fusion"]


def test_parse_args_qt_style_equals_form_keeps_file() -> None:
    args, unknown = parse_args(["-style=Fusion", "regs.md"])
    assert args.file == Path("regs.md")
    assert unknown == ["-style=Fusion"]


def test_parse_args_qt_flag_before_file_does_not_consume_path() -> None:
    args, unknown = parse_args(["-reverse", "regs.md"])
    assert args.file == Path("regs.md")
    assert unknown == ["-reverse"]


def test_help_includes_file_argument() -> None:
    help_text = build_argument_parser().format_help()
    assert "Markdown CSR file to open on launch" in help_text
