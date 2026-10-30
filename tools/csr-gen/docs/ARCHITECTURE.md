# Architecture

`csr-gen` converts CSR interface descriptions between supported file formats.

## Audience And Source Of Truth

The tool serves system architects, RTL designers, and firmware engineers.

**Markdown is the authoritative specification.** Readers import Markdown into the
shared register model; serializers generate downstream artifacts from that model.
Import from IP-XACT is implemented for migration (including SPIRIT 1685-2009 XML
and `--ipxact-address-block` for large multi-peripheral maps); SystemRDL import
is implemented for the Phase 1 subset documented in [`SYSTEMRDL.md`](SYSTEMRDL.md).
Generated outputs are not authoritative over the Markdown source.

## Implemented Capabilities

Markdown import, validation, Markdown export, IP-XACT import/export, AXI4-Lite
SystemVerilog RTL, and C headers are implemented. Additional buses and interchange
formats are planned.

The high-level pipeline is:

```text
Input file -> Format-specific reader -> Intermediate CSR model
Intermediate CSR model -> Format-specific serializer -> Output file
```

Each supported input format has a reader that parses its source representation
into a shared intermediate data structure. Implemented readers include Markdown,
IP-XACT, and SystemRDL (Phase 1 subset); see [`SYSTEMRDL.md`](SYSTEMRDL.md).

The `RegisterModel` contains 32-bit, 4-byte-aligned registers and their fields.
This register width is a permanent project constraint. Address gaps between
registers are legal.

### Field Access

Access keywords in the Markdown table map to the shared model and must follow
SystemRDL and IP-XACT semantics for hardware behavior. The `none` access means
reserved: reads return the programmed reset value and writes are ignored. See
`docs/DEVELOPMENT.md` for the Markdown-to-SystemRDL behavior table.

Markdown validation through `csr-gen validate` collects every illegal table row
before raising an error. No register model is produced when any row fails.

### Markdown Table Rules

A named section may contain multiple CSR tables: at most one table in the
section body and at most one table per subsection (a heading deeper than the
section heading). Registers from every table merge into one `RegisterModel`;
legality checks (duplicate names, addresses, overlapping fields) apply across
all tables. Subsection headings are organizational only; generated RTL is still
one block for the section.

Each register is introduced by a register definition row (`Register` and
`Address` with empty `Field`, `Bits`, `Access`, and `Reset`) or a combined row
that also names the first field. Field rows omit `Register` and `Address` and
must leave `HW Access` empty; non-empty values on field rows are rejected.
Every register needs at least one field row. Combined-row Markdown (register
and first field on one line) remains valid input and may carry `HW Access` on
that row; Markdown and CSV export always emit a register definition row first.

Required input columns are `Register`, `Address`, `Field`, and `Bits`. `Access`,
`Description`, `HW Access`, and `Reset` are optional (see README register table
reference). When the `Reset` column is omitted, every field reset value is `0`;
when it is present, each row must supply a non-empty reset value.

When serializing back to Markdown, column order is fixed to match the README:
`Register`, `Address`, `Field`, `Bits`, `Access`, `Reset`, `HW Access`,
`Description`. Markdown, CSV, IP-XACT, SystemRDL, C header, and SystemVerilog
exports sort registers by address (low to high) and tabular field rows by LSB
(low to high) via `csr_gen.output.register_order`.

### Address Map

Markdown `Address` values are **byte offsets within the CSR block**, not
system-level absolute addresses. Gaps between offsets are legal.

For AXI4-Lite RTL, use a **base address plus offset** scheme:

- Expose a `BASE_ADDR` parameter with default `0` so the block works without
  required instantiation parameters.
- Treat each table address as a byte offset from `BASE_ADDR`.
- Decode register selects from `axi_awaddr` / `axi_araddr` after subtracting
  `BASE_ADDR` (or equivalent range checks on the full address).

This matches typical SoC integration (relocate the block with one parameter) and
keeps the Markdown map readable as a local offset table starting at `0x00`.

The AXI address decode path is **auto-sized** from the model: it spans byte
offsets `0` through the highest inclusive last-byte address in the table
(including that register's occupied bytes). Address gaps in the table remain
undecoded. Helper functions `register_decoder_byte_high()` and
`register_decoder_addr_width()` in `csr_gen.model` define the bounds for RTL
generation. Inclusive address ranges use a **last-byte** end
(for example `0x20-0x2F` or `0x8000-0x15FFFF`). Generated AXI4-Lite
`s_axi_awaddr` / `s_axi_araddr` ports (and their registered copies) use that
decoder width; `BASE_ADDR` stays a 32-bit parameter and data remains 32-bit.

## Code Layout

| Package path | Role |
| --- | --- |
| `csr_gen.model` | Shared `RegisterModel`, validation, decoder sizing |
| `csr_gen.input` | Markdown and YAML readers |
| `csr_gen.output` | Markdown and YAML serializers |

`csr_gen.input.markdown_reader` uses `markdown-it-py` to locate one named Markdown
section and its single CSR table. `csr_gen.input.yaml_reader` imports a direct YAML
representation of the model for tests and interchange. Both readers invoke the
shared legality checks in `csr_gen.model`.

`csr_gen.output.markdown_writer` renders the normalized model back to a Markdown
register table in the fixed README column order. `csr_gen.output.yaml_writer`
dumps the model for inspection and golden tests.

Each additional output format adds a serializer under `csr_gen.output`.
Implemented serializers include SystemVerilog RTL, C headers, IP-XACT, SystemRDL,
and Simics DML 1.4. See [`IPXACT.md`](IPXACT.md) and [`SYSTEMRDL.md`](SYSTEMRDL.md)
for interchange assumptions.

## CLI

| Command | Role |
| --- | --- |
| `validate` | Parse and check Markdown; optional `--dump-model` to stdout |
| `generate` | Parse once, emit one or more `--output-file` / `--output-format` pairs |
| `generate-rtl`, `convert` | Deprecated hidden aliases that forward to `generate` |

`generate` accepts output formats `markdown`, `systemverilog` (`sv`),
`c-header` (`c`), `dml`, `ip-xact`, and `systemrdl`. `--interface-type` applies to
SystemVerilog outputs in that invocation.

Keeping parsing and serialization separate allows one normalized CSR model to
support multiple input and output formats without direct format-to-format
converters.

## AXI4-Lite RTL Generation

The first RTL serializer targets an AXI4-Lite slave with these assumptions:

| Topic | Decision |
| --- | --- |
| Module parameters | None required at instantiation; optional parameters such as `BASE_ADDR` use defaults |
| Typedefs / packages | Not generated |
| Clocking | Single clock for the register bank |
| Reset | Single synchronous reset for the bank |
| Reset values | Applied on synchronous reset from the Markdown `Reset` column; no separate power-on-reset model (FPGA target) |
| Strobes | AXI4-Lite `wstrb` / byte strobes supported |
| Security / privilege | Not supported |
| Interrupts / events | Not supported |

`csr_gen.output.systemverilog_writer` generates the version-1 AXI4-Lite slave.
The module name is the Markdown section heading in lower case with spaces replaced
by underscores (for example `CSR Registers` → `csr_registers`). Module ports are
ordered by register address (low to high) and field MSB (high to low). Reserved
(`none`) fields have no ports. Internal registers expose per-field `_q` (continuous
register output), `_q_upd` (one-cycle pulse after Q updates), `_d` (hardware load
data), and `_d_wen` (load enable with priority over AXI writes). Software-readable
and software-writable access semantics apply on the AXI path; `_d`/`_d_wen` load
directly into the flop. External registers use register-level delegate ports
(`_wren`, `_rden`, `_wstrb`, `_wdata`, `_rdata`, `_rdatavalid`, and ranged
`_waddr` / `_raddr`). `BASE_ADDR` is a module parameter (default zero). Register byte offsets are
`localparam` constants used in address decode. Generated RTL includes ASCII
register-map and per-register field tables in `//` comments (shared formatting
with C headers via `csr_gen.output.ascii_tables`). Each register is emitted in
its own section with address decode, field outputs, a dedicated `always_comb`
read path, and a dedicated `always_ff` update block. A single `always_ff` holds
AXI4-Lite pending state; a final `always_comb` muxes per-register read data onto
`s_axi_rdata`. Golden regression output lives in `specs/golden/*/expected.sv`.

## C Header Generation

`csr_gen.output.c_header_writer` renders firmware headers from the normalized model.
Naming follows the Markdown section heading: `CSR Registers` yields macro prefix
`CSR_REGISTERS`, include guard `CSR_REGISTERS_H`, and typedef prefix `csr_registers`.

| Topic | Decision |
| --- | --- |
| Base address | Overridable `CSR_REGISTERS_BASE_ADDR` (default zero); per-register `*_ADDR` macros add offset and base |
| `none` fields | Omitted from field macros and struct bitfields; still included in register-level `*_RESET` |
| Field API | Generic `_GET(reg)` / `_SET(reg, val)` macros on a local `uint32_t`; platform `reg_read` / `reg_write` documented only |
| Documentation | Top-level usage comment and ASCII register map; per-register ASCII field tables (including `none` rows) |
| stdint / C++ | Assembly guard, `stdint.h` / `cstdint`, and `extern "C"` per project convention |
| Section | `--markdown-section` required when generating from Markdown (and for naming) |

Golden regression output lives in `specs/golden/*/expected.h`.

## Logging

`csr_gen.logging` wraps Python standard-library logging for consistent CLI
behavior. Reported errors terminate the command with a non-zero exit status.
The CLI `--warnings-as-errors` option promotes reported warnings to errors.

## Golden Specifications

Reference CSR Markdown files live under `specs/golden/`. Each case directory
contains `regs.md`, `section.txt`, and `model.yml`. Unit tests in
`tests/unittests/test_golden_specs.py` discover cases automatically. See
`specs/golden/README.md` for conventions and how to add negative-test trees
later.
