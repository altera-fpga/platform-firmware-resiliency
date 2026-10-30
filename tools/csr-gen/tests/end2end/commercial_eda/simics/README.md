# Simics DML end-to-end tests

Each case builds generated `csr_registers.dml` as a Simics module and runs
Python tests with the workspace `bin/test-runner`.

## Layout

```text
simics/
  .gitignore              # Workspace outputs and generated csr_registers.dml
  common.sh               # Shared init, DML generation, build, test-runner
  test_simics.py          # pytest wrapper (`example-device`, `external-device`, `cca-accel`)
  <case>/
    section.txt           # Optional; else specs/golden/<case>/section.txt
    test.sh               # Manual / pytest entry point (cca-accel sets INPUT_MD)
    modules/csr-registers/
      Makefile
      module_load.py
      test/               # Checked-in Simics Python tests (SUITEINFO sets the 600 s suite timeout)
      csr_registers.dml   # Generated each run (gitignored)
```

The Simics workspace root files (`bin/`, `GNUmakefile`, `simics`, etc.) are
created by `simics_intelfpga_cli --reinitialize` on the first run and are not
checked in. The checked-in module skeleton under `modules/csr-registers/` is
preserved across reinitialize.

## Run

After `make install`, install Simics (freely available) and put
`simics_intelfpga_cli` on `PATH`:

```bash
make test-end2end-commercial-eda
tests/end2end/commercial_eda/simics/example-device/test.sh
tests/end2end/commercial_eda/simics/cca-accel/test.sh
```

`cca-accel` reads `tests/testdata/cca_accel.md` (52-register DMA +
accelerator map) instead of a golden `regs.md`.

The pytest wrapper fails fast when `simics_intelfpga_cli` is not on `PATH`.

`test.sh` runs `bin/test-runner -v` and always prints
`logs/test/linux64/modules/csr-registers/test/test.log` after the run (including
on failure) so CI and local logs capture full Simics test output.
