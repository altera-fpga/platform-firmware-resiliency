# Development

## Product Milestones

User-visible capabilities are summarized in README **Key features**. The
feature-to-test map lives in [`TEST_PLAN.md`](TEST_PLAN.md) (each implemented
row must have test coverage).

Markdown remains the source of truth for register definitions. YAML import exists
for tests and direct model construction only.

## Contributing and AI policy

- [CONTRIBUTING.md](../CONTRIBUTING.md) — contribution workflow, tests, licensing
- [AI_POLICY.md](../AI_POLICY.md) — use of AI tools in this repository
- [LICENSE.md](../LICENSE.md) — MIT-0 (MIT No Attribution)
- [skills/csr-markdown/](skills/csr-markdown/) — portable Agent Skill users copy
  into their own repo or AI tool to author Markdown CSR maps (not a
  `.cursor` / `.agents` skill in this tree)

When Markdown table rules change (README register table reference or parser
behavior), update `docs/skills/csr-markdown/references/TABLE_RULES.md` and the
skill `assets/` in the same change. Optionally run `skills-ref validate
./docs/skills/csr-markdown` if that CLI is installed; it is not a `make`
dependency.

## User examples document

[`EXAMPLES.md`](EXAMPLES.md) is generated from `specs/golden/` reference outputs.
After changing golden `expected.md`, `expected.sv`, or `expected.h` files, run:

```sh
make doc-examples
make doc-examples-check
```

## Source Layout

Python modules are grouped by data-flow role:

| Path | Role |
| --- | --- |
| `src/csr_gen/model.py` | Shared register model and validation |
| `src/csr_gen/input/` | Parsers (Markdown, IP-XACT, YAML) |
| `src/csr_gen/output/` | Serializers (Markdown, IP-XACT, YAML, SystemVerilog, C) |
| `src/csr_gen/cli.py` | Command-line interface |
| `src/csr_gen_gui/` | Optional desktop GUI (`csr-gen-gui`) |

Import parsers and serializers from `csr_gen.input` and `csr_gen.output`, or from
their specific modules.

### GUI (optional)

The GUI is an optional install extra; the CLI wheel does not require PySide6.

```sh
pip install -e ".[gui]"    # development: CLI + GUI dependencies
make install-gui           # alias for make install (GUI enabled by default)
work/csr-gen/bin/csr-gen-gui
make test-gui              # headless document-layer tests (no display required)
make test-gui-smoke        # Qt main window smoke test (editable install + PySide6)
```

Headless logic lives in `csr_gen_gui.document.DocumentController`, `table_editing.py`,
`bitfield_editing.py`, and `address_map.py`. Qt widgets are under
`src/csr_gen_gui/widgets/` (`CsrTableWidget`, `BitfieldCanvas`, `AddressMapWidget`).

### Markdown Round-Trip

```sh
venv/bin/csr-gen generate \
  --input-file specs/golden/example-device/regs.md \
  --input-format markdown \
  --markdown-section "CSR Registers" \
  --output-file work/normalized.md \
  --output-format markdown
```

Repeat `--output-file` and `--output-format` to emit several artifacts from one
parsed model (input is read once). The option counts must match. Supported output
formats include `markdown`, `systemverilog` (alias `sv`), `c-header` (alias `c`),
`ip-xact`, and `systemrdl`. Use `--interface-type` for SystemVerilog outputs.

The deprecated `convert` and `generate-rtl` commands forward to `generate`.

`csr-gen` logs `INFO` lines for the input path, Markdown section (when
applicable), each output path, and a successful `validate` result.

`output/markdown_writer.py` emits the fixed README column order. Round-trip
normalizes names to uppercase, reformats addresses and resets, and strips inline
Markdown from imported cells.

### Address Decoder Sizing

RTL generation will auto-size the byte-offset decoder from the highest register
address in the model. Use `register_decoder_byte_high()` and
`register_decoder_addr_width()` in `csr_gen.model` for the computed bounds.

## Environment

### End-user install (documented in README)

Users of `csr-gen` should **not** use `make venv` or `requirements.txt`. From a
clone or source tree, a normal install is:

```sh
python3 -m venv venv
source venv/bin/activate
pip install .
```

That installs runtime dependencies from `pyproject.toml` only. README **Getting
started** describes this flow; the sections below are for repository development.

### Development virtual environment

Create the development virtual environment:

```sh
make venv
```

The development environment installs `requirements.txt` and installs `csr-gen`
in editable mode (`pip install -e .`).

Runtime dependencies required by the installed `csr-gen` command belong in the
`[project].dependencies` list in `pyproject.toml`. To add a runtime dependency:

1. Add the package requirement to `[project].dependencies`.
2. Add or update tests for the behavior that uses the dependency.
3. Run `make test-unittests`.
4. Run `make test-smoketest`.
5. Run `make style-check`.

For example:

```toml
[project]
dependencies = [
  "click>=8.4,<9",
  "example-package>=1.0,<2",
]
```

The top-level `requirements.txt` defines the repo development and test
environment. Add packages there only when they are needed by repo-level tools,
tests, or developer workflows. A package may appear in both files when the
development environment also needs direct access to a runtime dependency.

## Build And Install

Build the wheel and source distribution:

```sh
make build
```

Install the built wheel into the end-to-end test environment:

```sh
make install
```

The install target creates `work/csr-gen/venv/`, installs `requirements.txt`
and the built `csr-gen` wheel (with the GUI extra by default), and writes
wrapper scripts under `work/csr-gen/bin/`. Override the install root with
`INSTALL_ROOT=/path/to/root`; disable the GUI with `make install INSTALL_GUI=0`
(only the `csr-gen` wrapper is created).

From the repository root, build the files to attach to a GitHub release:

```sh
make csr-gen-release-assets
```

That writes `csr_gen-<version>-py3-none-any.whl`, `csr_gen-<version>.tar.gz`,
and `csr-markdown.zip` into the top-level `install/` directory. Attach those
three files to the release. The release description covers the whole
repository. Do not attach this document or the README as release assets.

`make test-all` uses a separate environment at `work/test-all-venv` that adds
PeakRDL packages (`requirements-eda.txt`), the GUI extra (`PySide6`), and the
same dev dependencies as unit tests. Commercial EDA tools (`quartus_syn`, `vcs`,
Simics) are still required on `PATH` for synthesis and simulation
tests; the Python packages alone do not skip PeakRDL or GUI tests.

## Golden Specifications

Reference register maps for tests and agents are under `specs/golden/`. Each case
is a subdirectory with:

| File | Purpose |
| --- | --- |
| `regs.md` | Markdown source-of-truth specification |
| `section.txt` | Section heading passed to `--markdown-section` |
| `model.yml` | Expected normalized model (same schema as the YAML test reader) |
| `expected.md` | Expected normalized Markdown from `write_markdown()` |

`tests/unittests/test_golden_specs.py` runs four checks per case:

| Test | Path |
| --- | --- |
| `test_golden_markdown_matches_model` | `regs.md` model equals `model.yml` |
| `test_golden_yaml_export_matches_expected` | `model.yml` → Markdown equals `expected.md` (generator only) |
| `test_golden_expected_markdown_round_trip` | `expected.md` → model → Markdown is idempotent |
| `test_golden_regs_markdown_export_matches_expected` | `regs.md` → model → Markdown equals `expected.md` |

Regenerate `expected.md` from `model.yml` when the writer changes. See
`specs/golden/README.md` for the three-oracle layout.

Golden cases may include `expected.sv` (AXI4-Lite SystemVerilog from `model.yml`).
Regenerate `expected.h` from `model.yml` when the C header writer changes.

Negative examples live under `specs/golden-reject/`. Each case includes
`error.txt` with a substring expected in the validation output.
`tests/unittests/test_golden_reject_specs.py` discovers those cases automatically.

## Validate Markdown Input

Check a Markdown CSR specification before generation:

```sh
venv/bin/csr-gen validate \
  --input-file specs/golden/example-device/regs.md \
  --markdown-section "CSR Registers"
```

Dump the normalized internal model as YAML:

```sh
venv/bin/csr-gen validate \
  --input-file specs/golden/example-device/regs.md \
  --markdown-section "CSR Registers" \
  --dump-model
```

Validation collects **all** illegal table rows and model problems, reports them
together, and does not build a register model when any error is present.

**Row numbers in errors:** For **CSV**, `CSR table row N` matches spreadsheet
line numbers (row 1 is the header). For **Markdown**, row numbers count from the
first data row only (the header and separator lines are not numbered). Multiline
quoted CSV cells still form one logical row; physical file line numbers can
differ from the reported row when descriptions span multiple lines.

### Register And Field Legality

- Registers are fixed **32-bit** words with **4-byte-aligned** addresses.
- **Full bit coverage is not required.** Bits not described by any field are
  unimplemented in hardware.
- **Fields must not overlap** within a register, including fields with `none`
  access.
- A section may include one CSR table in the section body and/or one table per
  subsection (deeper heading). All tables merge into one model; duplicate
  register names or addresses across tables are rejected.
- Register definition rows set `Register`, `Address`, optional `Description`,
  and `HW Access` with empty `Field`, `Bits`, `Access`, and `Reset`; at least one
  field row must follow. Combined rows (register plus first field) remain valid
  input. Markdown and CSV export always write a register definition row before
  field rows.
- Every field row must include non-empty `Field` and `Bits` cells. `HW Access`
  must be empty on field rows; a non-empty value is rejected (not merely
  compared to the register definition row).
- CSV input uses the same column rules as Markdown (one table per file, RFC
  4180 quoting). Pass `--input-format csv` and optional `--csr-name` (defaults
  to the file stem). Export with `--output-format csv`.
- `Access`, `Description`, `HW Access`, and `Reset` are optional columns. Empty
  or missing `Access` defaults to `rw` on field rows. Empty or missing
  `Description` defaults to the field name on field rows and the register name
  on register definition rows; on a combined row it sets both descriptions. When
  the `Reset` column is omitted, every field reset value is `0`; when it is
  present, each field row must supply a non-empty reset value.

### Access Keywords And SystemRDL

Markdown `Access` values map to SystemRDL-style field behavior:

| Markdown | SystemRDL-style behavior |
| --- | --- |
| `none` | Reserved: `sw=r`; reads return reset; writes ignored |
| `ro` | Read-only: `sw=r` |
| `rc` | Read-only, `onread` clears |
| `rw` | Read/write: `sw=rw` |
| `wo` | Write-only: `sw=w` |
| `r0w1c` | Read returns zero; write-1-to-clear |
| `rw1s` | Read/write; write-1-to-set |
| `rw1c` | Read/write; write-1-to-clear |
| `rw0c` | Read/write; write-0-to-clear |

## Internal Reader APIs

The initial library APIs import Markdown and YAML descriptions into the shared
register model:

```python
from pathlib import Path

from csr_gen.input.markdown_reader import load_markdown_file
from csr_gen.input.yaml_reader import load_yaml_file
from csr_gen.output.markdown_writer import write_markdown_file
from csr_gen.output.systemverilog_writer import write_systemverilog_file
from csr_gen.output.yaml_writer import dump_model_yaml

markdown_spec = load_markdown_file(Path("regs.md"), "CSR Registers")
markdown_model = markdown_spec.model
yaml_model = load_yaml_file(Path("regs.yml"))
print(dump_model_yaml(markdown_model))
```

The YAML reader exists for testing and direct model construction. It uses a
representation of the normalized register model:

```yaml
registers:
  - name: CTRL
    address: 0x00
    description: Control register
    fields:
      - name: ENABLE
        msb: 0
        lsb: 0
        access: rw
        reset: 0
        description: Enable field
```

## Testing

See [`TEST_PLAN.md`](TEST_PLAN.md) for the feature-to-test coverage map.

Run the required tests for every change:

```sh
make test-unittests
make test-smoketest
```

The unit-test lane reports Python source coverage for `csr_gen` with
`pytest-cov`. The smoke-test lane checks the basic installed-package script.
The convenience target `make test` runs unit tests, the installed-package smoke
test, and C header compile-and-run tests (`tests/end2end/c_header_compile/`; requires
`gcc`).

Tests are organized by scope:

- `tests/unittests/`: pytest unit tests for Python modules and CLI behavior.
- `tests/end2end/smoketest/`: installed-package smoke tests.
- `tests/end2end/c_header_compile/`: generate C headers from golden Markdown,
  compile `test.c` with strict GCC flags, and run runtime GET/SET checks (see
  `tests/end2end/c_header_compile/README.md`).
- `tests/end2end/eda/`: opt-in end-to-end EDA workflow integration tests.
- `tests/end2end/commercial_eda/`: end-to-end tests that require Quartus,
  VCS, or Simics on `PATH`. Quartus is freely available. Quartus CSR synthesis lives under
  `tests/end2end/commercial_eda/quartus_sv_compile/` (see its `README.md`).
  VCS functional simulation (Intel `altera_axi4lite_mm_manager` BFM) lives under
  `tests/end2end/commercial_eda/vcs_sim/` (see its `README.md`; reuses each case's
  `quartus_sv_compile/<case>/csr_synth_harness.sv`).

Useful focused targets:

```sh
make test-unittests
make test-smoketest
make test-c-header-compile
make test-end2end-eda
# Commercial EDA requires Quartus, VCS, or Simics on PATH:
make test-end2end-commercial-eda
make test-all
make test-all-venv   # rebuild work/test-all-venv only
make coverage-html
```

`make test-all` depends on `make install`, prepends `work/csr-gen/bin` on `PATH`
for subprocess `csr-gen` / `csr-gen-gui` calls, and runs pytest from
`work/test-all-venv` (PeakRDL and related tools stay on that venv's `bin`).
After `make install`, the Makefile exports `work/csr-gen/bin` on `PATH` for other
targets (`test-smoketest`, `test-c-header-compile`, and similar).

**Parallel end2end runs:** `pytest-xdist` is enabled for `make test-c-header-compile`,
`make test-smoketest`, `make test-end2end-eda`, and
`make test-end2end-commercial-eda` (default `-n auto` workers). Disable with
`PYTEST_XDIST=0` or cap workers with `PYTEST_WORKERS=4`. Unit tests
(`make test-unittests`) stay serial for stable coverage.

`make test-smoketest` runs the basic script smoke tests against the install
wrappers under `work/csr-gen/bin`. Run it for every change.

Run `make test-end2end-eda` only when integration testing is needed.

Commercial EDA requires the appropriate tools on `PATH`. Quartus and Simics
are freely available. VCS is for users who already have it:

```sh
make test-end2end-commercial-eda
make test-all
```

`make coverage-html` runs all tests and writes a browsable source coverage
report to `htmlcov/index.html`. Run it only when the EDA environments and
commercial licenses required by the opt-in lanes are available.

Remove the installed-package test environment:

```sh
make clean
```

## Style Checks

Run formatting and lint validation:

```sh
make style-check
```

`make style-format` is reserved for explicit human-requested formatting.
