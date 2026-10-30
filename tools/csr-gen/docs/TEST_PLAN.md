# Test Plan

This document maps **implemented behavior** to automated tests. It is for
contributors and agents, not for day-to-day `csr-gen` usage.

When you add or change user-facing behavior:

1. Add or extend tests so behavior stays covered.
2. Add a row to the tables below (and a bullet in README **Key features**).
3. Run `make test-unittests` and `make test-smoketest`.

Future work is promoted here (and to README **Key features**) when implemented.
Priority order: P1 Linux headers
→ P2 Verible → P3 VCS warnings → P4 SVD → P5 bus interfaces → P6 optional
regression → P7 optional `dmlc`.

## Test gaps

Open checklist for **missing or thin coverage**. Remove rows here when tests
land; add rows to the feature tables below at the same time. Priorities follow
the product roadmap.

### P1 — Linux kernel–style headers

| Gap | Add when | Suggested coverage |
| --- | --- | --- |
| Linux kernel header export | Serializer and CLI format land | `tests/unittests/test_linux_header_writer.py` (or shared module tests); golden `expected*.h` under `specs/golden/`; `test_cli.py` for `--output-format`; compile check under `tests/end2end/` (kernel-style headers with `gcc -Werror`, or sparse/kernel build smoke if available) |
| Distinct from `c-header` | Same milestone | Assert firmware `c_header_writer` output unchanged; golden oracles must not conflate GET/SET macro headers with kernel-style output |

Implementation may use a new `src/csr_gen/output/linux_header_writer.py` or extend
`c_header_writer.py` only if kernel and firmware layouts share enough structure;
pick one module boundary during P1 and test accordingly.

### P2 — Verible formatting on generated RTL

| Gap | Add when | Suggested coverage |
| --- | --- | --- |
| Verible-formatted SystemVerilog | Formatter integrated in `systemverilog_writer` | Snapshot or golden tests on formatted output; optional `verible-verilog-lint` (or project-standard Verible check) when tool is on `PATH` |

### P3 — VCS strict warnings and lint

| Gap | Add when | Suggested coverage |
| --- | --- | --- |
| VCS warning/lint gate | Strict `vcs` flags agreed and wired in `vcs_sim/common.sh` | Unit tests for log/report parser (mirror `tests/unittests/test_syn_report_check.py`); fail `tests/end2end/commercial_eda/vcs_sim/` when `sim.log` (or designated reports) contain warnings; document flags in `vcs_sim/README.md` |

Today VCS tests check functional simulation only; they do **not** yet fail on
compiler warnings (unlike Quartus synthesis report checking).

### P4 — SVD import and export

| Gap | Add when | Suggested coverage |
| --- | --- | --- |
| SVD reader/writer | SVD interchange implemented | `tests/unittests/test_svd_reader.py`, `test_svd_writer.py`; golden round-trip under `specs/golden/`; CLI tests in `test_cli.py` |

### P5 — SystemVerilog bus interfaces

| Gap | Add when | Suggested coverage |
| --- | --- | --- |
| Avalon-MM / AXI4 / APB SystemVerilog | Bus serializers implemented | `tests/unittests/test_systemverilog_writer.py` golden oracles; `specs/golden/*/expected-*.sv` or per-interface files; `tests/end2end/commercial_eda/quartus_sv_compile/` and `vcs_sim/` cases per interface (including P3 warning gate when enabled) |

### P6 — Optional regression expansion

Pull forward when a specific vendor map or migration fails. Default priority **after P1–P5**.

| Gap | Notes | Suggested coverage |
| --- | --- | --- |
| IP-XACT register arrays beyond flat `dim` | Large vendor maps | Targeted fixtures under `tests/testdata/ipxact/` |
| SystemRDL vendor / PeakRDL fixtures | Not in default `make test-end2end-eda` gate | `tests/end2end/eda/` opt-in cases |
| IEEE 1685 XSD validation | Tooling not implemented | Unit tests on valid/invalid XML when validator exists |

### P7 — Simics `dmlc` compile (optional)

| Gap | Notes | Suggested coverage |
| --- | --- | --- |
| Simics `dmlc` compile | Golden `expected.dml` compared in unit tests; compile optional | `tests/end2end/commercial_eda/simics/` or dedicated compile script |

### Deferred GUI features

No automated tests until the feature is implemented.

### Shipped-behavior gaps (deep review 2026-09-14)

| Gap | Notes | Suggested coverage |
| --- | --- | --- |
| `validate` for IP-XACT / SystemRDL | `csr-gen validate` accepts only `markdown` and `csv` (`src/csr_gen/cli.py`); `generate` accepts all `INPUT_FORMATS` | **Needs decision**. If extended: CLI tests for selectors (`--ipxact-address-block`, `--systemrdl-addrmap`) and `--dump-model`, parallel to generate paths |
| Contributor docs vs package layout | ARCHITECTURE / DEVELOPMENT / AGENTS still describe Markdown+YAML-centric `input`/`output` packages | Doc-only; no new tests — see TODO deep-review docs hygiene |

## Markdown input and validation

| Feature | Test coverage |
| --- | --- |
| Parse a CSR table from a named Markdown section (case-insensitive heading match) | `tests/unittests/test_markdown_reader.py`, `tests/unittests/test_golden_specs.py` |
| Import and export CSV tables (RFC 4180; `--csr-name`; canonical columns) | `tests/unittests/test_csv_reader.py`, `tests/unittests/test_csv_writer.py`, `tests/unittests/test_cli.py` |
| Golden CSV cases (`specs/golden/csv/`: combined + canonical split rows) | `tests/unittests/test_golden_csv_specs.py` |
| CSV reader errors (empty file, unreadable path, `csv.Error`, blank rows) | `tests/unittests/test_csv_reader.py` |
| Real-world CSV fixture (multiline descriptions, continuations, address range) | `test_load_pqc_ip_csv`, `tests/testdata/pqc_ip.csv`, `tests/end2end/c_header_compile/pqc-ip/` (CSV → Markdown → C header compile) |
| Real-world Markdown fixture (H1 DMA + accelerator sections; multi-subsection tables) | `tests/unittests/test_cca_accel.py`, `tests/testdata/cca_accel.md`, `tests/end2end/c_header_compile/cca-accel/`, `tests/end2end/commercial_eda/quartus_sv_compile/cca-accel/`, `tests/end2end/commercial_eda/simics/cca-accel/`, `tests/end2end/commercial_eda/vcs_sim/cca-accel/` |
| Shared table parser (`parse_csr_table`, register-definition rows) | `tests/unittests/test_table_reader.py` |
| IP-XACT reader error and literal edge cases | `tests/unittests/test_ipxact_reader.py` |
| ASCII table width fallback and CSV address ranges | `tests/unittests/test_ascii_tables.py`, `test_write_csv_formats_address_ranges` |
| YAML `hw_access` type validation | `test_load_yaml_rejects_malformed_schema` (`hw_access must be a string`) |
| Accept flexible column order and inline Markdown in cells on input | `test_load_markdown_file_accepts_reordered_columns_and_complex_document` |
| Multiple CSR tables (one per subsection) merged into one model | `test_load_markdown_merges_tables_from_subsections` |
| Reject duplicate addresses across subsections | `test_load_markdown_rejects_duplicate_address_across_subsections` |
| Reject more than one table in section body or subsection | `test_load_markdown_file_rejects_ambiguous_document` (`two_tables.md`, `two_tables_one_subsection.md`) |
| Optional `Access` / `Description` columns and empty cells (`rw`, field-name defaults) | `test_load_markdown_accepts_table_without_optional_columns`, `test_load_markdown_defaults_empty_access_and_description_cells` |
| Optional `Reset` column (omit column → reset `0`; present column requires every cell) | `test_load_markdown_defaults_reset_when_column_omitted`, `test_load_markdown_rejects_empty_reset_when_column_present`, `testdata/optional_no_reset_column.md` |
| Reordered table without optional columns | `test_load_markdown_file_accepts_reordered_columns_without_optional_columns` |
| Normalize register and field names to uppercase in `RegisterModel` | `test_load_markdown_from_memory_normalizes_model`, `test_markdown_round_trip_normalizes_names_and_formatting` |
| Validate 32-bit registers with 4-byte-aligned addresses | `tests/unittests/test_model.py` |
| Support SystemRDL/IP-XACT-aligned access keys (`none`, `ro`, `rc`, `rw`, `rw1c`, and others) | `test_validate_model_accepts_supported_access_definitions`, `test_load_markdown_runs_model_legality` |
| Report every illegal table row in one validation pass (no partial model on error) | `test_load_markdown_reports_all_invalid_rows`, `test_validate_reports_multiple_errors` |
| Allow address gaps and registers without full 32-bit field coverage | `test_validate_model_accepts_aligned_address_gaps_and_nonzero_base` |
| Portable Agent Skill `docs/skills/csr-markdown` (frontmatter + parseable assets) | `tests/unittests/test_csr_markdown_skill.py` |
| Optional `HW Access` column (`internal` default, `external`); only on register definition or combined rows | `test_load_markdown_parses_hw_access_and_address_range`, `test_load_markdown_defaults_hw_access_to_internal`, `test_load_markdown_rejects_hw_access_on_field_row`, `test_load_markdown_rejects_hw_access_on_continuation_row`, `test_load_csv_rejects_hw_access_on_field_row` |
| Inclusive address ranges on `Address` (last-byte end, e.g. `0x20-0x2F` / `0x8000-0x15FFFF`); external-only; one `31:0` field | `test_load_markdown_parses_hw_access_and_address_range`, `test_register_range_helpers_for_multi_slot_external_range`, `test_validate_model_accepts_last_byte_inclusive_range`, `test_validate_model_rejects_internal_address_range` |
| Reject invalid `HW Access`, malformed ranges, and range field bit layout | `test_load_markdown_rejects_invalid_hw_access_and_ranges`, `test_validate_model_rejects_address_range_with_multiple_fields`, `test_validate_model_rejects_address_range_with_wrong_bit_span`, `specs/golden-reject/invalid-hw-access`, `internal-address-range`, `address-range-wrong-bits`, `unaligned-address` |
| Reject register and field names with spaces or special characters | `tests/unittests/test_names.py` |
| Parse address and reset as hexadecimal literals (bare digits are base 16) | `tests/unittests/test_literals.py`, `tests/unittests/test_table_reader.py` |
| Reject invalid golden specs under `specs/golden-reject/` | `tests/unittests/test_golden_reject_specs.py` |

## IP-XACT input and output

| Feature | Test coverage |
| --- | --- |
| Import minimal IP-XACT (single memory map, field access, `oneToClear` → `rw1c`) | `tests/unittests/test_ipxact_reader.py`, `testdata/ipxact_minimal.xml` |
| Reject multi-block IP-XACT without `--ipxact-address-block`; import one block (block-local offsets) | `testdata/ipxact_multi_block.xml`, `test_ipxact_reader.py`, `test_cli.py` |
| Reject `<register>` directly under `<memoryMap>` | `test_rejects_register_directly_under_memory_map` |
| SPIRIT 1685-2009 namespace on import | `test_loads_spirit_2009_namespace_component` |
| Reject multiple memory maps, overlaps, malformed XML, unsupported access | `test_rejects_multiple_memory_maps`, `test_rejects_overlapping_fields`, `test_rejects_malformed_xml`, `test_rejects_unsupported_access` |
| IP-XACT XML round-trip on minimal fixture | `tests/unittests/test_ipxact_writer.py` (`test_ipxact_round_trip`) |
| Export/import `HW Access`, address ranges (`dim`), `none`/`r0w1c` via csr-gen vendor extensions | `test_ipxact_extensions.py`, `test_import_register_hw_access_and_address_range`, `test_ipxact_export_preserves_external_range_and_hw_access`, `test_ipxact_export_preserves_none_and_r0w1c_access` |
| Golden `external-device` model round-trip via IP-XACT | `test_external_device_ipxact_golden_round_trip` |
| Golden `expected.xml` byte match for `example-device` and `external-device` | `test_golden_yaml_export_matches_expected_xml` |
| Export uses sanitized component/memory-map identifiers for PeakRDL | `test_ipxact_export_uses_sanitized_identifiers_for_peakrdl` |
| Memory-map `<description>` becomes Markdown section heading on csr-gen export import | `test_memory_map_description_becomes_section_heading_for_csr_gen_export` |
| Third-party memory-map `<description>` does not override `<name>` section heading | `test_memory_map_description_ignored_for_third_party_import` |
| IP-XACT → Markdown → model on minimal fixture | `test_ipxact_import_to_markdown_round_trip` |
| `generate --input-format ip-xact` (default section heading = memory map `name`, or csr-gen `description`) | `test_generate_ipxact_input_defaults_section`, `test_generate_ipxact_to_systemverilog_without_explicit_section`, `test_generate_ipxact_to_dml_without_explicit_section`, `test_generate_ipxact_to_c_header_without_explicit_section` |
| `generate --input-format csv` to C header and DML (section heading from file stem) | `test_generate_csv_to_c_header_and_dml` |
| `generate --output-format ip-xact` from Markdown | `test_generate_ipxact_output` |
| Golden `expected.xml` for `example-device` and `external-device` | `specs/golden/*/expected.xml` |
| PeakRDL-ipxact `dump` smoke tests on golden XML | `tests/end2end/eda/peakrdl/test_peakrdl_ipxact_golden.py`, `make test-end2end-eda` |

## SystemRDL input and output

| Feature | Test coverage |
| --- | --- |
| Export golden `expected.rdl` for `example-device` and `external-device` | `tests/unittests/test_systemrdl_writer.py` |
| Model round-trip via SystemRDL import | `tests/unittests/test_systemrdl_reader.py` |
| Import native flat third-party RDL without csr-gen field UDPs | `tests/testdata/systemrdl/native_flat.rdl`, `test_load_systemrdl_imports_native_third_party_rdl` |
| Import legacy `csr_gen_address_end` ranged registers | `test_load_systemrdl_imports_legacy_address_end_udp` |
| Reject non-32-bit `regwidth`; import hierarchical regfiles and nested addrmaps | `test_load_systemrdl_rejects_non_32bit_registers`, `tests/testdata/systemrdl/hierarchical_*.rdl`, `test_load_systemrdl_requires_addrmap_selector_for_multi_peripheral` |
| Multi-peripheral import requires `--systemrdl-addrmap` | `test_generate_systemrdl_addrmap_filter`, `test_load_systemrdl_imports_selected_nested_addrmap` |
| Golden SystemRDL elaborates with `systemrdl-compiler` | `tests/unittests/test_systemrdl_elaborate.py` |
| Import Leon2-style RDL with unset field `reset` property | `test_load_systemrdl_imports_leon2_uart_with_unset_field_reset`, `tests/testdata/systemrdl/SystemRDL_1.0/Examples/Leon2/uart.rdl` |
| Accellera 1.0 import to Markdown (counter, lock-and-key, Leon2 uart/gpio) | `tests/end2end/eda/accellera/test_accellera_import.py`, `make test-end2end-eda` |
| Accellera `generic_rdl` import expected failure (signals, Perl, mem) | `tests/end2end/eda/accellera/test_accellera_generic_rdl.py` |
| PeakRDL `html` and `regblock` smoke tests on golden RDL | `tests/end2end/eda/peakrdl/test_peakrdl_golden.py`, `make test-end2end-eda` |
| Access mapping helpers | `tests/unittests/test_systemrdl_access.py` |
| `generate --input-format systemrdl` and `--output-format systemrdl` | `tests/unittests/test_cli.py` |

See [`SYSTEMRDL.md`](SYSTEMRDL.md) for the supported subset and validation strategy.

## Command-line interface

| Feature | Test coverage |
| --- | --- |
| `validate` — check Markdown without writing output | `test_validate_succeeds_for_valid_markdown` |
| `validate --dump-model` — print normalized model as YAML | `test_validate_dump_model_writes_yaml` |
| `generate` — one parse, multiple `--output-file` / `--output-format` pairs | `test_generate_writes_multiple_outputs_in_one_run` |
| `generate` output formats: `markdown`, `systemverilog` (`sv`), `c-header` (`c`), `dml`, `ip-xact`, `systemrdl` | `test_generate_markdown_round_trip`, `test_generate_systemverilog_writes_axi4lite_rtl`, `test_generate_c_header_output`, `test_generate_dml_output`, `test_generate_ipxact_output`, `test_generate_systemrdl_output`, `test_generate_ipxact_to_c_header_without_explicit_section`, `test_generate_csv_to_c_header_and_dml` |
| Reject mismatched output option counts and missing Markdown section | `test_generate_requires_matching_output_option_counts`, `test_generate_requires_markdown_section`, `test_generate_dml_requires_markdown_section` |
| `--warnings-as-errors`, non-zero exit on errors, INFO logging | `tests/unittests/test_logging.py`, CLI `caplog` tests in `tests/unittests/test_cli.py` |
| Hidden deprecated aliases `generate-rtl` and `convert` forward to `generate` | `test_deprecated_generate_rtl_forwards_to_generate`, `test_deprecated_convert_forwards_to_generate` |
| Install wrappers under `work/csr-gen/bin/` | `tests/unittests/test_install_wrappers.py`, `scripts/write_install_wrapper.sh` |
| C header compile-and-run from golden Markdown (`gcc`, strict warnings) | `tests/end2end/c_header_compile/test_c_header_compile.py` (`example-device`, `external-device`, `multi-subsection-tables`, `optional-no-reset-column`, `pqc-ip`, `cca-accel`) |
| Quartus synthesis (`quartus_syn` on `PATH`; Quartus is freely available) | `tests/end2end/commercial_eda/quartus_sv_compile/` (`example-device`, `external-device`, `cca-accel`; `test_quartus_sv_compile.py`); report parser `tests/unittests/test_syn_report_check.py`; harness `tests/unittests/test_synth_test_harness_writer.py` |
| VCS functional simulation (`vcs` on `PATH`; `altera_axi4lite_mm_manager` from Quartus `sim_lib`) | `tests/end2end/commercial_eda/vcs_sim/` (`example-device`, `external-device`, `cca-accel`; `test_vcs_sim.py`); reuses `quartus_sv_compile/<case>/csr_synth_harness.sv`. **Planned (P3):** strict warning/lint flags and `sim.log` warning scan — see [Test gaps § P3](#p3--vcs-strict-warnings-and-lint) |
| Simics DML module build and register-bank tests (`simics_intelfpga_cli` on `PATH`, `bin/test-runner`; Simics is freely available) | `tests/end2end/commercial_eda/simics/` (`example-device`, `external-device`, `cca-accel`; `test_simics.py`); generates `modules/csr-registers/csr_registers.dml` per run |

## Generated outputs

| Feature | Test coverage |
| --- | --- |
| Register definition rows (import, export, legacy combined rows) | `test_load_markdown_accepts_register_definition_rows`, `test_golden_expected_markdown_round_trip`, `test_golden_regs_markdown_export_matches_expected` |
| Markdown export with fixed canonical column order (includes `HW Access`) | `tests/unittests/test_markdown_writer.py`, `test_golden_expected_markdown_round_trip`, `test_golden_regs_markdown_export_matches_expected` (`external-device`) |
| Serializer register/field ordering (address and LSB sort on export) | `tests/unittests/test_register_order.py`, `src/csr_gen/output/register_order.py` |
| Preserve source section heading on Markdown export | `test_write_markdown_preserves_source_section_heading_with_mixed_case_query`, `test_generate_markdown_preserves_source_section_heading` |
| AXI4-Lite SystemVerilog CSR slave (default `--interface-type axi4-lite`); address ports sized from map span | `tests/unittests/test_systemverilog_writer.py`, `test_golden_regs_markdown_export_matches_expected_sv`, `test_axi_address_ports_sized_from_map_span` |
| SystemVerilog writer edge paths (file I/O, deferred read, helper fallbacks) | `test_write_systemverilog_file_writes_output`, `test_register_read_always_comb_internal_deferred_read`, `test_external_read_helper_empty_register_list`, `test_response_logic_empty_register_list`, `test_field_read_expr_reads_storage_when_no_field_port` |
| RTL: internal field ports `_q`, `_q_upd`, `_d`, `_d_wen` | `test_golden_regs_markdown_export_matches_expected_sv`, `test_write_systemverilog_includes_reset_and_access_logic` |
| RTL: ASCII register map, per-register logic, reset/access behavior, field port ordering | `test_write_systemverilog_includes_ascii_register_map`, `test_write_systemverilog_includes_reset_and_access_logic`, `test_field_ports_follow_register_and_msb_order` |
| RTL: read-only internal registers driven from `_d` with `_d_wen` (no write path) | `test_write_systemverilog_hw_only_register_uses_input_updates` |
| RTL: external registers (`_wren`, `_rden`, `_wstrb`, `_wdata`, `_rdata`, `_rdatavalid`) | `test_write_systemverilog_external_register_ports`, `test_write_systemverilog_external_read_only_register`, `test_write_systemverilog_external_write_only_register` |
| RTL: external address ranges (`_waddr` / `_raddr` index ports) | `test_write_systemverilog_external_range_register_ports`, `test_write_systemverilog_external_read_only_range_ports`, `test_write_systemverilog_external_write_only_range_ports` |
| Golden `external-device` SystemVerilog oracle | `test_golden_external_device_matches_expected_sv` |
| Golden `external-device` model and Markdown oracles | `test_golden_markdown_matches_model`, `test_golden_regs_markdown_export_matches_expected` (parametrized `external-device`) |
| Reject unimplemented SystemVerilog bus interfaces (for example APB) | `test_write_systemverilog_rejects_unsupported_interface` |
| C header: offsets, masks, GET/SET macros, usage comments | `tests/unittests/test_c_header_writer.py`, `test_golden_regs_markdown_export_matches_expected_h` |
| C header: compile and runtime exercise under GCC (`-Werror`) | `tests/end2end/c_header_compile/` (golden and testdata Markdown cases) |
| Linux kernel–style headers | **Planned (P1)** — see [Test gaps § P1](#p1--linux-kernelstyle-headers); distinct from firmware `c-header` above |
| Synthesizable test harness `csr_synth_harness.sv` (AXI + `reg_obs` top; LFSR-driven `_d`/`_d_wen` and XOR on `_q` for internal fields; embedded SRAM for external registers) | `tests/unittests/test_synth_test_harness_writer.py`, `scripts/generate_synth_test_harness.py`; checked-in `tests/end2end/commercial_eda/quartus_sv_compile/{example-device,external-device,cca-accel}/csr_synth_harness.sv` |
| DML export (Simics 1.4 device + bank; field templates from `utility.dml`; ranged registers as arrays) | `tests/unittests/test_dml_writer.py`, `test_generate_dml_output`, `test_generate_ipxact_to_dml_without_explicit_section`; golden oracles `specs/golden/{example-device,external-device}/expected.dml` |

## GUI (`csr-gen-gui`)

| Feature | Test coverage |
| --- | --- |
| Multi-bank document load/save with canonical Markdown and preserved prose | `tests/gui/test_document.py` |
| Surface open failures (duplicate headings, en-dash addresses, non-CSR subsection tables) | `tests/gui/test_document_load_errors.py`, `tests/unittests/test_literals.py` |
| Import IP-XACT, SystemRDL, and CSV (replace document); export active bank artifacts | `tests/gui/test_import_export.py`, `src/csr_gen_gui/import_export.py` |
| Table row ↔ `RegisterModel` conversion | `tests/gui/test_model_table.py` |
| In-process SV / C / DML / SystemRDL / IP-XACT preview generation | `tests/gui/test_document.py` (`test_generate_previews_match_golden_oracles`) |
| Preview syntax highlighting for SystemVerilog, C, DML, SystemRDL, and IP-XACT | `tests/gui/test_syntax_highlighting.py`, `src/csr_gen_gui/syntax_highlighting.py` |
| View menu preview pane visibility toggles | `tests/gui/test_preview_panes.py`, `src/csr_gen_gui/preview_panes.py` |
| Register table Sort button and Edit → Sort register table | `tests/gui/test_phase2_helpers.py` (`sort_table_rows`, `table_rows_need_sort`); manual `csr-gen-gui` |
| Address and reset cell commit normalization to `0x` hex | `tests/gui/test_table_legality.py`, `csr_gen.literals` |
| Register and field identifier validation (shared with CLI) | `tests/unittests/test_names.py`, `tests/gui/test_table_legality.py` |
| Bitfield move/resize with gap visualization, per-bit ruler ticks, and overlap rejection | `tests/gui/test_phase2_helpers.py`, `tests/gui/test_bitfield_canvas.py`; `src/csr_gen_gui/widgets/bitfield_canvas.py` |
| Address map timeline with gaps, conflicts, and register selection | `tests/gui/test_phase2_helpers.py`, `tests/gui/test_address_map_widget.py`; `src/csr_gen_gui/widgets/address_map_widget.py` |
| Address map y-axis ruler ticks at register boundaries | `tests/gui/test_phase2_helpers.py` (`timeline_ruler_ticks`, external-device golden); `src/csr_gen_gui/address_map.py` |
| Preview monospace font | `src/csr_gen_gui/main_window.py` (`Courier`) |
| Undo/redo for document edits (Edit menu; Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z) | `tests/gui/test_editor_snapshot.py`, `tests/gui/test_undo_redo.py`, `src/csr_gen_gui/editor_snapshot.py`, `src/csr_gen_gui/undo_commands.py` |
| GUI headless suite (no full window) | `make test-gui` — `tests/gui/` except smoke |
| GUI offscreen smoke (constructs main window) | `make test-gui-smoke` — `tests/gui/test_main_window_smoke.py` |
| Qt main window (manual spot-check) | Launch `csr-gen-gui` or `work/csr-gen/bin/csr-gen-gui` after `make install` |

## Test infrastructure

| Feature | Test coverage |
| --- | --- |
| Full pytest sweep (`make test-all`) | all of `tests/` including `tests/end2end/commercial_eda/` when present |
| Regenerate `docs/EXAMPLES.md` from golden outputs (`make doc-examples`) | `tests/unittests/test_generate_examples_doc.py`, `make doc-examples-check` |
| Golden cases under `specs/golden/<case>/` (oracles: `model.yml`, `expected.md`, optional `expected.sv` / `expected.h` / `expected.dml`) | `tests/unittests/test_golden_specs.py` |
| YAML model load/dump for tests and `--dump-model` | `tests/unittests/test_yaml_reader.py`, `tests/unittests/test_yaml_writer.py` |

See [`specs/golden/README.md`](../specs/golden/README.md) and
[`specs/golden-reject/README.md`](../specs/golden-reject/README.md) for layout
and adding cases.
