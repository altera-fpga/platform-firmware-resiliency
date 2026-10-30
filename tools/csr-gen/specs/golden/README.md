# Golden CSR Specifications

This directory holds **reference Markdown CSR specifications** used by unit tests,
future RTL end-to-end tests, and agent workflows. Each case is a self-contained
example of a valid (or intentionally invalid) register map.

For a user-oriented walkthrough with sample outputs, see
[`docs/EXAMPLES.md`](../../docs/EXAMPLES.md) (`make doc-examples` regenerates it).

## Layout

Each immediate subdirectory under `specs/golden/` is one test case:

```text
specs/golden/<case-name>/
  regs.md        # Realistic author input (source of truth in production)
  section.txt    # Single line: Markdown section heading to parse
  model.yml      # Semantic oracle for the normalized register model
  expected.md    # Canonical Markdown export (markdown_writer output)
```

## Three Oracles

Each golden case uses three related artifacts. Tests exercise different paths
through the pipeline:

| File | Role | Primary test |
| --- | --- | --- |
| `model.yml` | Normalized register model (semantic truth) | `test_golden_markdown_matches_model` |
| `expected.md` | Canonical table export from the writer | `test_golden_yaml_export_matches_expected` |
| `regs.md` | Realistic Markdown with reordered columns, inline markup, etc. | `test_golden_regs_markdown_export_matches_expected` |

### Test pyramid

```text
regs.md --parse--> model <--load-- model.yml          # semantics
                      |
                      +--write_markdown--> expected.md   # YAML -> MD (generator only)
                      |
expected.md --parse--> model --write_markdown--> expected.md  # idempotent canonical MD
                      |
regs.md --parse--> model --write_markdown--> expected.md      # integrated path
```

- **`test_golden_yaml_export_matches_expected`** isolates the Markdown **generator**
  (no Markdown parser involved).
- **`test_golden_expected_markdown_round_trip`** tests parser + writer on canonical
  `expected.md` only.
- **`test_golden_regs_markdown_export_matches_expected`** tests the full author
  input path; `regs.md` and `expected.md` are not required to match byte-for-byte.

Optional serializer oracles:

- `expected.sv` — golden AXI4-Lite SystemVerilog (`tests/unittests/test_systemverilog_writer.py`)
- `expected.h` — golden C header for firmware output tests
- `expected.dml` — golden Simics DML 1.4 device (`tests/unittests/test_dml_writer.py`, `tests/end2end/commercial_eda/simics/`)
- `expected.rdl` — golden SystemRDL addrmap with native register arrays for ranged
  registers (`tests/unittests/test_systemrdl_writer.py`, `test_systemrdl_elaborate.py`,
  `tests/end2end/eda/peakrdl/`)
- `expected.xml` — golden IP-XACT component export (`tests/unittests/test_ipxact_writer.py`,
  `tests/end2end/eda/peakrdl/test_peakrdl_ipxact_golden.py`)
- `README.md` — human notes for the case (design intent, not parsed by tools)

## Adding A Case

1. Create `specs/golden/<case-name>/`.
2. Write `regs.md` using the table rules in the top-level `README.md`.
3. Set `section.txt` to the exact section heading text (matching is
   case-insensitive).
4. Capture the normalized model as `model.yml` (see `docs/DEVELOPMENT.md`).
5. Generate `expected.md` from **`model.yml`** (not from messy `regs.md`):

   ```python
   from pathlib import Path
   from csr_gen.input.yaml_reader import load_yaml_file
   from csr_gen.output.markdown_writer import write_markdown_file

   case = Path("specs/golden/<case-name>")
   section = case.joinpath("section.txt").read_text().strip()
   model = load_yaml_file(case / "model.yml")
   write_markdown_file(case / "expected.md", model, section)
   ```

   Or use `csr-gen generate --output-format markdown` after ensuring `regs.md`
   parses to the same model as `model.yml`.
6. Run `make test-unittests` — `test_golden_specs.py` discovers every case
   directory automatically.

## Negative Cases

Invalid specifications live under [`specs/golden-reject/`](../golden-reject/README.md).
See that README for layout and `tests/unittests/test_golden_reject_specs.py`.

## CSV Golden Cases

Split-row and combined-row CSV examples live under [`csv/`](csv/README.md).
They share the same `model.yml` semantics as the Markdown `example-device` case.

## Relationship To `tests/testdata/`

`testdata/` holds small, focused inputs for parser edge cases (malformed tables,
duplicate headings, and similar). `specs/golden/` holds realistic, documented
examples meant to stay stable as product references.
