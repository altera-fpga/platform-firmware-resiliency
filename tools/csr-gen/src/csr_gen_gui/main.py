"""Entry point for csr-gen-gui."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# QApplication / QGuiApplication options that take a following argument.
# Values must be removed before argparse sees the optional file positional.
_QT_OPTIONS_WITH_VALUE = frozenset(
    {
        "-display",
        "-font",
        "-geometry",
        "-platform",
        "-platformpluginpath",
        "-platformtheme",
        "-plugin",
        "-qwindowgeometry",
        "-qwindowicon",
        "-qwindowtitle",
        "-session",
        "-style",
        "-stylesheet",
    }
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Return the csr-gen-gui command-line parser."""
    parser = argparse.ArgumentParser(
        prog="csr-gen-gui",
        description="Edit CSR Markdown files with validation and artifact previews.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="Markdown CSR file to open on launch",
    )
    return parser


def _split_qt_options(argv: list[str]) -> tuple[list[str], list[str]]:
    """Pull Qt option/value pairs out of argv before the optional file is parsed."""
    remaining: list[str] = []
    qt_argv: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        option = token.split("=", 1)[0]
        if option in _QT_OPTIONS_WITH_VALUE:
            qt_argv.append(token)
            index += 1
            if (
                "=" not in token
                and index < len(argv)
                and not argv[index].startswith("-")
            ):
                qt_argv.append(argv[index])
                index += 1
            continue
        remaining.append(token)
        index += 1
    return remaining, qt_argv


def parse_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    """Parse csr-gen-gui arguments, leaving unknown flags for Qt."""
    source = list(sys.argv[1:] if argv is None else argv)
    file_argv, qt_argv = _split_qt_options(source)
    args, unknown = build_argument_parser().parse_known_args(file_argv)
    return args, [*qt_argv, *unknown]


def main(argv: list[str] | None = None) -> None:
    """Launch the CSR Markdown editor GUI."""
    args, qt_argv = parse_args(argv)
    program_name = sys.argv[0] if argv is None else "csr-gen-gui"

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "csr-gen-gui requires the optional gui dependency.\n"
            "Install with: pip install 'csr-gen[gui]'",
            file=sys.stderr,
        )
        raise SystemExit(1) from None

    application = QApplication([program_name, *qt_argv])
    from csr_gen_gui.main_window import create_main_window

    window = create_main_window()
    if args.file is not None:
        if not window.open_document_path(args.file.resolve(), confirm_discard=False):
            raise SystemExit(1)
    window.show()
    raise SystemExit(application.exec())


if __name__ == "__main__":
    main()
