# C header compile end-to-end tests

Each subdirectory is one compile-and-run harness. The directory name matches
`specs/golden/<case-name>/` when the input is a golden `regs.md`; testdata-driven
cases use the same layout with `section.txt` and a Makefile `INPUT_MD` pointing at
`tests/testdata/*.md`.

Per-case `Makefile` targets:

1. **generate** — `csr-gen generate` from Markdown into `build/regs.h`
2. **compile** — `test.c` plus shared sources under `inc/` with strict GCC flags
3. **run** — execute the test binary (runtime GET/SET checks)

Shared code under `inc/`:

| File | Role |
| --- | --- |
| `reg_access_mock.c` / `.h` | In-memory `reg_read` / `reg_write` |
| `c_header_test.c` / `.h` | `CHECK`, timing, PASS/FAIL summary |
| `c_header_case.mk` | Markdown → C header, compile / run |
| `c_header_csv_case.mk` | CSV → Markdown → C header, compile / run |
| `c_header_ipxact_case.mk` | IP-XACT → Markdown → C header; optional `IPXACT_ADDRESS_BLOCK` (private tests) |
| `c_header_test_flags.mk` | `-std=c11`, `-Werror`, and related flags |

Format checked-in sources with `make format` in a case directory or
`make style-format-clang` at the repo root (only `tests/end2end/c_header_compile/**`
C/H files; excludes `build/`).

Pytest runs every case via `test_c_header_compile.py` (`make test` per directory).

## Cases

| Directory | Markdown input |
| --- | --- |
| `example-device` | `specs/golden/example-device/regs.md` |
| `external-device` | `specs/golden/external-device/regs.md` |
| `multi-subsection-tables` | `tests/testdata/multi_subsection_tables.md` |
| `optional-no-reset-column` | `tests/testdata/optional_no_reset_column.md` |
| `pqc-ip` | `tests/testdata/pqc_ip.csv` (CSV → Markdown → C header) |
| `cca-accel` | `tests/testdata/cca_accel.md` (`CSR Registers`) |

## Adding a case

1. Ensure the Markdown source exists (golden or `testdata/`).
2. Copy `example-device/` to `tests/end2end/c_header_compile/<name>/`.
3. Set `INPUT_MD` and `SECTION` (or `section.txt`) in the new `Makefile`.
4. Write `test.c` to exercise every register macro you care about.
5. Add `<name>` to `CASES` in `tests/end2end/c_header_compile/Makefile` and to
   `_CASES` in `test_c_header_compile.py`.
6. Run `make test-c-header-compile`.

Cases are not discovered automatically until those lists are updated.
