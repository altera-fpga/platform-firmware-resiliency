#!/usr/bin/env python3
"""Generate docs/EXAMPLES.md from specs/golden reference outputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "specs" / "golden"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "EXAMPLES.md"

CASES = (
    {
        "id": "example-device",
        "title": "Example device (internal registers)",
        "summary": (
            "A small map with **internal** registers only. The author `regs.md` "
            "uses flexible column order, inline Markdown in cells, and extra "
            "prose around the table. `csr-gen` normalizes names, adds the "
            "`HW Access` column on export, and generates an AXI4-Lite slave with "
            "per-field `_q`, `_q_upd`, `_d`, and `_d_wen` ports."
        ),
    },
    {
        "id": "external-device",
        "title": "External device (delegated registers and ranges)",
        "summary": (
            "Shows **external** registers: a mixed FIFO register, and inclusive "
            "address ranges (`0x20-0x2F`) with a single `31:0` field for memory-style "
            "windows. RTL exposes `_wren`, `_rden`, `_wstrb`, `_wdata`, `_rdata`, "
            "`_rdatavalid`, and `_waddr` / `_raddr` on ranged externals."
        ),
    },
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fence(lang: str, body: str) -> str:
    body = body.rstrip("\n")
    return f"```{lang}\n{body}\n```\n"


def _demote_headings(md: str, *, extra_levels: int = 3) -> str:
    """Demote ATX headings so embedded Markdown nests under EXAMPLES.md."""
    lines: list[str] = []
    for line in md.splitlines():
        if not line.startswith("#"):
            lines.append(line)
            continue
        hashes = len(line) - len(line.lstrip("#"))
        if hashes == 0 or line[hashes] not in " \t":
            lines.append(line)
            continue
        new_level = min(hashes + extra_levels, 6)
        lines.append("#" * new_level + line[hashes:])
    return "\n".join(lines).rstrip("\n") + "\n\n"


def _source_and_rendered(md: str, *, intro: str) -> str:
    return "\n".join(
        [
            intro + "\n",
            "#### Source\n",
            _fence("markdown", md),
            "#### Rendered\n",
            _demote_headings(md),
        ]
    )


def _rel_link(path: Path) -> str:
    return Path("..").joinpath(path.relative_to(REPO_ROOT)).as_posix()


def _extract_sv_register_map(sv_text: str) -> str:
    lines: list[str] = []
    in_map = False
    for line in sv_text.splitlines():
        if line.strip() == "// Register map":
            in_map = True
            continue
        if not in_map:
            continue
        if line.startswith("// +") or line.startswith("// |"):
            lines.append(line.removeprefix("// "))
            continue
        if lines and not line.startswith("//"):
            break
    return "\n".join(lines)


def _extract_sv_ports(sv_text: str) -> str:
    lines: list[str] = []
    in_ports = False
    for line in sv_text.splitlines():
        if "// Register interfaces" in line:
            in_ports = True
            lines.append(line)
            continue
        if in_ports:
            if line.strip() == ");":
                break
            lines.append(line)
    return "\n".join(lines)


def _extract_sv_snippet(sv_text: str, marker: str, *, max_lines: int = 35) -> str:
    lines: list[str] = []
    capturing = False
    for line in sv_text.splitlines():
        if marker in line:
            capturing = True
            lines.append(line)
            continue
        if not capturing:
            continue
        if line.startswith("// ---") and len(lines) > 1:
            break
        lines.append(line)
        if len(lines) >= max_lines:
            lines.append("    // ...")
            break
    return "\n".join(lines)


def _extract_h_register_map(h_text: str) -> str:
    lines: list[str] = []
    in_map = False
    for line in h_text.splitlines():
        if "Register map" in line and line.strip().startswith("*"):
            in_map = True
            continue
        if not in_map:
            continue
        if line.strip().startswith("* +") or line.strip().startswith("* |"):
            lines.append(line.strip().removeprefix("* ").rstrip())
            continue
        if line.strip() == "*/" and lines:
            break
    return "\n".join(lines)


def _extract_h_defines(h_text: str, *, limit: int = 12) -> str:
    picked: list[str] = []
    for line in h_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#define CSR_REGISTERS_"):
            continue
        if "_ADDR" in stripped or "_GET(" in stripped or "_SET(" in stripped:
            picked.append(stripped)
        if len(picked) >= limit:
            break
    return "\n".join(picked)


def _extract_dml_register_map(dml_text: str) -> str:
    lines: list[str] = []
    in_map = False
    for line in dml_text.splitlines():
        if line.strip() == "// Register map":
            in_map = True
            continue
        if not in_map:
            continue
        if line.startswith("// +") or line.startswith("// |"):
            lines.append(line.removeprefix("// "))
            continue
        if lines and not line.startswith("//"):
            break
    return "\n".join(lines)


def _extract_dml_snippet(dml_text: str, marker: str, *, max_lines: int = 20) -> str:
    lines: list[str] = []
    capturing = False
    for line in dml_text.splitlines():
        if marker in line:
            capturing = True
            lines.append(line)
            continue
        if not capturing:
            continue
        if line.startswith("    // ---") and len(lines) > 1:
            break
        lines.append(line)
        if len(lines) >= max_lines:
            lines.append("    // ...")
            break
    return "\n".join(lines)


def _case_section(case: dict[str, str]) -> str:
    case_id = case["id"]
    case_dir = GOLDEN_ROOT / case_id
    section = _read(case_dir / "section.txt").strip()
    regs_md = _read(case_dir / "regs.md")
    expected_md = _read(case_dir / "expected.md")
    sv_text = _read(case_dir / "expected.sv")
    h_text = _read(case_dir / "expected.h")
    dml_text = _read(case_dir / "expected.dml")

    if case_id == "example-device":
        sv_snippet_marker = "// --- CTRL @"
        dml_snippet_marker = "// --- CTRL @"
    else:
        sv_snippet_marker = "// --- FIFO @"
        dml_snippet_marker = "// --- MEM @"

    commands = f"""csr-gen validate \\
  --input-file specs/golden/{case_id}/regs.md \\
  --markdown-section "{section}"

csr-gen generate \\
  --input-file specs/golden/{case_id}/regs.md \\
  --input-format markdown \\
  --markdown-section "{section}" \\
  --output-file work/{case_id}.sv \\
  --output-format systemverilog \\
  --output-file work/{case_id}.h \\
  --output-format c-header \\
  --output-file work/{case_id}.dml \\
  --output-format dml \\
  --output-file work/{case_id}.normalized.md \\
  --output-format markdown"""

    output_links = (
        f"- [`regs.md`]({_rel_link(case_dir / 'regs.md')}) — "
        "Markdown specification you author\n"
        f"- [`expected.md`]({_rel_link(case_dir / 'expected.md')}) — "
        "normalized Markdown table export\n"
        f"- [`expected.sv`]({_rel_link(case_dir / 'expected.sv')}) — "
        "complete AXI4-Lite SystemVerilog module\n"
        f"- [`expected.h`]({_rel_link(case_dir / 'expected.h')}) — "
        "complete C register header\n"
        f"- [`expected.dml`]({_rel_link(case_dir / 'expected.dml')}) — "
        "complete Simics DML 1.4 device\n"
    )

    return "\n".join(
        [
            f"## {case['title']}\n",
            case["summary"] + "\n",
            f"Reference specification: [`specs/golden/{case_id}/`]"
            f"({_rel_link(case_dir)})\n",
            "### Commands\n",
            _fence("sh", commands),
            "### Author specification\n",
            _source_and_rendered(
                regs_md,
                intro=(
                    "The register map lives in human-readable Markdown—prose, "
                    "headings, and tables—not in a separate machine-only format. "
                    "Below is the bundled `regs.md` as you would author it (source) "
                    "and as it appears when rendered."
                ),
            ),
            "### Normalized Markdown\n",
            "Exported register table with optional columns filled in and "
            "explicit defaults (including `HW Access` when omitted in the "
            "source):\n",
            _fence("markdown", expected_md),
            "### SystemVerilog\n",
            "Generated module includes an AXI4-Lite slave, a register map "
            "comment, design-facing ports, and per-register logic. Excerpts:\n",
            "Register map:\n",
            _fence("text", _extract_sv_register_map(sv_text)),
            "Design-side ports:\n",
            _fence("systemverilog", _extract_sv_ports(sv_text)),
            f"Sample register logic:\n",
            _fence("systemverilog", _extract_sv_snippet(sv_text, sv_snippet_marker)),
            "### C header\n",
            "Generated header provides base/offset addresses, field get/set "
            "macros, and a register map comment. Excerpts:\n",
            "Register map:\n",
            _fence("text", _extract_h_register_map(h_text)),
            "Address and field macros:\n",
            _fence("c", _extract_h_defines(h_text)),
            "### Simics DML\n",
            "Generated DML describes a Simics 1.4 device and bank using "
            "`utility.dml` field templates. Ranged external registers become "
            "array declarations. Excerpts:\n",
            "Register map:\n",
            _fence("text", _extract_dml_register_map(dml_text)),
            f"Sample register declarations:\n",
            _fence("dml", _extract_dml_snippet(dml_text, dml_snippet_marker)),
            "### Complete output files\n",
            output_links,
        ]
    )


def build_document() -> str:
    header = """# Examples

Walkthroughs of two bundled register maps and the outputs `csr-gen` produces
from each. **Markdown is the source of truth:** you document registers in
readable prose and tables, then generate RTL and headers from that spec. Use
the commands in each section with your own `regs.md` files by changing the
input paths.

## Generated outputs

From a Markdown CSR table, `csr-gen` can emit:

- **Normalized Markdown** — canonical register table with optional columns
  filled in (including `HW Access` when omitted in the source).
- **SystemVerilog** — AXI4-Lite slave wrapper, register map documentation,
  design-facing ports (`_q`, `_q_upd`, `_d`, and `_d_wen` for internal fields; additional
  handshake and address ports for external registers and ranges).
- **C header** — base address, per-register offsets, and field get/set macros
  for firmware.
- **Simics DML** — DML 1.4 device and bank for software simulation (field
  templates from `utility.dml`; ranged registers as arrays).

Bundled reference specs live under
[`specs/golden/`](../specs/golden/README.md).

"""
    body = "\n".join(_case_section(case) for case in CASES)
    footer = (
        "\n## See also\n\n"
        "- [README](../README.md) — installation, CLI usage, and register "
        "table rules\n"
    )
    return header + body + footer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write (default: docs/EXAMPLES.md)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if output would change the existing file",
    )
    args = parser.parse_args()

    document = build_document()
    if args.check:
        if not args.output.is_file():
            print(f"Missing {args.output}; run make doc-examples", file=sys.stderr)
            return 1
        existing = _read(args.output)
        if existing != document:
            print(
                f"{args.output} is out of date; run make doc-examples", file=sys.stderr
            )
            return 1
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
