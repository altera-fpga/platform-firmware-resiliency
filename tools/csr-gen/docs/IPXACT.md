# IP-XACT support

`csr-gen` reads and writes IEEE 1685-2014 IP-XACT component XML for CSR register
maps. Import also accepts SPIRIT 1685-2009 XML (for example Magillem exports) by
matching element local names regardless of namespace prefix. Markdown remains the
authoritative specification; IP-XACT is an interchange format for migration and
tool integration.

## Import

- Root element: `<component>` (for example `ipxact:component` or `spirit:component`).
- Exactly one `memoryMap`; its `name` becomes the default Markdown section heading
  unless `--markdown-section` overrides it. For components exported by csr-gen
  (`vendor` `csr-gen`), the memory-map `description` (human-readable section title)
  is used instead of `name`.
- Registers must live inside `<addressBlock>`; `<register>` elements directly
  under `<memoryMap>` are rejected.
- Each register must have `name`, `addressOffset`, and at least one `field` with
  `name`, `bitOffset`, `bitWidth`, and `access` (or a register-level default).
- `<addressOffset>` values are **block-local byte offsets** (peripheral base 0).
  `<baseAddress>` on an address block is not added to imported Markdown addresses.
- **Multiple address blocks:** files with more than one `<addressBlock>` require
  `--ipxact-address-block <name>` (exact match on `<addressBlock><name>`). Single-block
  files import without the flag.
- Verilog-style literals are accepted (`'h`, `'d`, `'b`, `0x`, decimal).
- Field access mapping:

| IP-XACT | `csr-gen` access |
| --- | --- |
| `read-write` | `rw` |
| `read-only` | `ro` |
| `write-only` | `wo` |
| `read-write` + `modifiedWriteValue` `oneToClear` | `rw1c` |
| `read-write` + `oneToSet` | `rw1s` |
| `read-write` + `zeroToClear` | `rw0c` |
| `read-only` + `clear` | `rc` |

csr-gen-specific access keywords not represented in base IP-XACT are preserved
with csr-gen vendor extensions under `http://csr-gen.dev/ipxact/1.0`:

| `csr-gen` access | Import / export |
| --- | --- |
| `none` | `<vendorExtensions><csrgen:access>none</csrgen:access>` (base `<access>` is `read-only`) |
| `r0w1c` | `<vendorExtensions><csrgen:access>r0w1c</csrgen:access>` (base `<access>` is `read-write`) |

Register `HW Access` and inclusive address ranges use the same namespace:

| `csr-gen` metadata | Import / export |
| --- | --- |
| `hw_access` `external` | `<vendorExtensions><csrgen:hwAccess>external</csrgen:hwAccess>` |
| Address range `0x20-0x2F` | `<dim>4</dim>`, `<dimIncrement>4</dimIncrement>`, optional `<csrgen:addressEnd>'h2f</csrgen:addressEnd>` |

Unsupported child elements under `component`, `memoryMap`, `addressBlock`,
`register`, and `field` produce a **single warning per element type** (honors
`--warnings-as-errors`). Registers without fields are skipped with a warning.

Registers with no fields, multiple memory maps, and overlapping fields are
rejected. There is **no XSD validation** in v1.

## Export

Export emits a minimal generated component (`vendor` `csr-gen`, `library`
`generated`) with one `memoryMap` and one `addressBlock` at `baseAddress` 0.
Component, memory-map, and address-block `name` elements use sanitized
identifiers derived from the Markdown section heading (for example `CSR Registers`
→ `csr_registers`); when the heading contains spaces, the human-readable text is
stored in `<memoryMap><description>`. Third-party vendor metadata from imported
files is not preserved except where mapped above; csr-gen round-trips its own
`vendorExtensions` and `dim` metadata.

Golden `expected.xml` files under `specs/golden/` are validated with PeakRDL-ipxact
(`peakrdl dump`) in `tests/end2end/eda/peakrdl/test_peakrdl_ipxact_golden.py`
via `make test-end2end-eda`.

## CLI examples

```sh
# IP-XACT → Markdown (section defaults to memory map name)
csr-gen generate \
  --input-file map.xml \
  --input-format ip-xact \
  --output-file regs.md \
  --output-format markdown

# Large map: import one peripheral (address block)
csr-gen generate \
  --input-file HPS_Reg_Map.xml \
  --input-format ip-xact \
  --ipxact-address-block "u_emac2__apb_reg_config_slave__10830000__DWCXG_CORE__SEG_L4_MP_emac2_s_0x0_0x10000" \
  --output-file work/emac2.md \
  --output-format markdown

# Markdown → IP-XACT
csr-gen generate \
  --input-file regs.md \
  --input-format markdown \
  --markdown-section "CSR Registers" \
  --output-file map.xml \
  --output-format ip-xact

# Optional explicit section / map name
csr-gen generate \
  --input-file map.xml \
  --input-format ip-xact \
  --markdown-section "CSR Registers" \
  --output-file regs.md \
  --output-format markdown

# IP-XACT → C header or Simics DML (section defaults to memory map name)
csr-gen generate \
  --input-file map.xml \
  --input-format ip-xact \
  --output-file regs.h \
  --output-format c-header

csr-gen generate \
  --input-file map.xml \
  --input-format ip-xact \
  --output-file device.dml \
  --output-format dml
```

## Tests

| Scope | Location |
| --- | --- |
| Minimal fixture and round-trip | `tests/testdata/ipxact_minimal.xml`, `test_ipxact_reader.py`, `test_ipxact_writer.py` |
| csr-gen vendor extensions (`hwAccess`, `addressEnd`, field `none`/`r0w1c`) | `test_ipxact_extensions.py`, `test_ipxact_reader.py`, `test_ipxact_writer.py` |
| Golden `expected.xml` oracles and external-device round-trip | `test_golden_yaml_export_matches_expected_xml`, `test_external_device_ipxact_golden_round_trip` |
| Multi-block selection | `tests/testdata/ipxact_multi_block.xml`, `test_ipxact_reader.py`, `test_cli.py` |
| CLI | `tests/unittests/test_cli.py` |
