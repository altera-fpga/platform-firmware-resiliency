---
name: csr-markdown
description: >-
  Author and edit csr-gen-compatible Markdown CSR register maps (named section,
  GitHub tables, 32-bit 4-byte-aligned offsets, SystemRDL-style access). Use
  when creating or updating a CSR interface, register map, hardware registers,
  AXI register block, or firmware header spec in Markdown for csr-gen validate
  or generate.
license: MIT-0
metadata:
  version: "1.0"
  csr-gen: "Markdown CSR tables for the csr-gen tool"
---

# csr-markdown

Write a **Markdown CSR specification** that `csr-gen` can validate and generate
from. Markdown is the source of truth. Do not treat generated SystemVerilog, C
headers, DML, IP-XACT, SystemRDL, or YAML `--dump-model` output as the spec.

## When to use

Use this skill when the user wants a new or updated **register map in Markdown**
for csr-gen (CSR block, MMIO map, AXI4-Lite programmable registers, field
tables). Do **not** use it to convert IP-XACT/SystemRDL (that is `csr-gen`
import) or to design non-32-bit registers.

## Install csr-gen

Prefer `csr-gen` already on `PATH`. If it is missing, tell the user to download
the `csr_gen-*-py3-none-any.whl` asset from the latest release at
<https://github.com/altera-fpga/platform-firmware-resiliency/releases> and run
`pip install` on that file. Do not install it for them. Until `csr-gen validate`
has been run, say the map is unvalidated.

## Instructions

1. Follow [references/WORKFLOW.md](references/WORKFLOW.md): interview, write,
   validate.
2. Before finishing, read [references/TABLE_RULES.md](references/TABLE_RULES.md).
3. Start from [assets/template.md](assets/template.md). See
   [assets/example-device.md](assets/example-device.md) for a small valid map
   (combined-row author style). Prefer **register definition rows** on new files.

### Interview checklist

- Output `.md` path and **exactly one** section heading (`--markdown-section`).
- Each register: name, byte **offset** (or `external` range), `HW Access`.
- Each field: name, bits, `Access`, reset, description.

### Write rules (short)

- Required columns: `Register`, `Address`, `Field`, `Bits`.
- New tables: `Register`, `Address`, `Field`, `Bits`, `Access`, `Reset`,
  `HW Access`, `Description`.
- 32-bit registers; 4-byte-aligned **block offsets**; address gaps OK.
- Access: `none`, `ro`, `rc`, `rw`, `r0w1c`, `rw1s`, `rw1c`, `rw0c`, `wo`.
- `HW Access` `internal`/`external` only on definition or combined rows.
- Ranges (`0x20-0x2F`) need `external` and one `31:0` field.

### Validate

If `csr-gen` is on `PATH`:

```sh
csr-gen validate \
  --input-format markdown \
  --input-file <path-to.md> \
  --markdown-section "<heading>"
```

If it is not installed, check TABLE_RULES.md and say the map is unvalidated.

Do not implement a second validator in this skill.
