#!/usr/bin/env python3
"""Regenerate checked-in synthesizable test harness for a synthesis compile case."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from csr_gen.input.ipxact_reader import load_ipxact_file
from csr_gen.input.markdown_reader import load_markdown_file
from csr_gen.output.synth_test_harness_writer import (
    SYNTH_HARNESS_FILENAME,
    write_synth_test_harness_sv,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "case_dir",
        type=Path,
        help="Case directory (e.g. tests/end2end/commercial_eda/quartus_sv_compile/example-device)",
    )
    parser.add_argument(
        "--input-md",
        type=Path,
        help="Markdown source (default: specs/golden/<case>/regs.md)",
    )
    parser.add_argument(
        "--input-xml",
        type=Path,
        help="IP-XACT source (private or vendor fixtures; overrides --input-md)",
    )
    parser.add_argument(
        "--ipxact-address-block",
        default=None,
        help="Address block name when --input-xml has multiple blocks",
    )
    parser.add_argument(
        "--section-file",
        type=Path,
        help="Section heading file (default: <case>/section.txt or golden section.txt)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=f"Exit non-zero if {SYNTH_HARNESS_FILENAME} would change",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    case_dir = args.case_dir.resolve()
    repo_root = _find_repo_root(case_dir)
    case_name = case_dir.name

    section_file = args.section_file or _section_file(case_dir, repo_root, case_name)

    if args.input_xml is not None:
        ipxact_spec = load_ipxact_file(
            args.input_xml.resolve(),
            address_block_name=args.ipxact_address_block,
        )
        section = (
            section_file.read_text(encoding="utf-8").strip()
            if section_file.exists()
            else ipxact_spec.section_heading
        )
        model = ipxact_spec.model
    else:
        input_md = (
            args.input_md or repo_root / "specs" / "golden" / case_name / "regs.md"
        )
        section = section_file.read_text(encoding="utf-8").strip()
        markdown_spec = load_markdown_file(input_md, section)
        model = markdown_spec.model

    rendered = write_synth_test_harness_sv(model, section_heading=section)
    target = case_dir / SYNTH_HARNESS_FILENAME

    if args.check:
        if not target.exists():
            print(f"Missing {target}", file=sys.stderr)
            return 1
        if target.read_text(encoding="utf-8") != rendered:
            print(
                f"{target} is out of date; run: python {Path(__file__).name} {case_dir}"
            )
            return 1
        return 0

    target.write_text(rendered, encoding="utf-8")
    print(f"Wrote {target}")
    return 0


def _section_file(case_dir: Path, repo_root: Path, case_name: str) -> Path:
    local = case_dir / "section.txt"
    if local.exists():
        return local
    return repo_root / "specs" / "golden" / case_name / "section.txt"


def _find_repo_root(start: Path) -> Path:
    path = start
    for _ in range(8):
        if (path / "pyproject.toml").exists() and (path / "src" / "csr_gen").is_dir():
            return path
        if path.parent == path:
            break
        path = path.parent
    raise SystemExit(f"Could not find repository root from {start}")


if __name__ == "__main__":
    raise SystemExit(main())
