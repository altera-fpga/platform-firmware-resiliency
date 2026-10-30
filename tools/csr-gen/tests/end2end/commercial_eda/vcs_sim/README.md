# VCS functional simulation tests

Each case compiles generated `csr_registers` RTL plus the checked-in
`csr_synth_harness.sv` from the matching Quartus synthesis case, drives the
AXI4-Lite slave with Intel's `altera_axi4lite_mm_manager` BFM from Quartus
`eda/sim_lib`, and checks basic register behavior in simulation.

The Intel simulation library is **not** copied into this repository. VCS compiles
`altera_lnsim.sv` from the Quartus install at run time.

## Layout

```text
vcs_sim/
  .gitignore              # VCS outputs and generated csr_registers.sv
  test_vcs_sim.py         # pytest wrapper (`example-device`, `external-device`, `cca-accel`)
  common.sh               # Shared VCS compile/run logic (sourced by case test.sh)
  <case>/
    section.txt           # Optional; else specs/golden/<case>/section.txt
    csr_sim_tb.sv         # Top testbench (altera_axi4lite_mm_manager + harness)
    test.sh               # Manual / pytest entry point
    csr_registers.sv      # Generated each run (gitignored)
    simv sim.log csrc/    # VCS outputs (gitignored)
```

`csr_synth_harness.sv` is reused from
`tests/end2end/commercial_eda/quartus_sv_compile/<case>/` so synthesis and
simulation share the same DUT wrapper.

## Requirements

- `csr-gen` on `PATH` (`make install`)
- Synopsys VCS (`vcs`) on `PATH` (for users who already have VCS)
- Quartus simulation library:
  - `${QUARTUS_ROOTDIR}/eda/sim_lib` when Quartus is on `PATH`, or
  - `QUARTUS_SIM_LIB` pointing at that directory

## Run

Install VCS and Quartus and put them on `PATH`:

```bash
make test-end2end-commercial-eda
tests/end2end/commercial_eda/vcs_sim/example-device/test.sh
```

The pytest wrapper fails fast if `vcs` is not on `PATH`.

## example-device checks

After reset, `csr_sim_tb.sv` obtains a `BaseAxiBfm` handle from
`u_axi.AXI4LITEMAN.bfm`, calls `m_reset()`, then issues transactions with
`put_transaction()` and `drive_transaction()`. Shared `axi4lite_bus.svh` declares
explicit AXI4-Lite wires; both `altera_axi4lite_mm_manager` and
`csr_synth_harness` connect to the same nets so the BFM drives the slave ports.

The synthesis harness includes an LFSR that drives internal `hw_access` loads.
During AXI register checks the testbench forces `_d_wen` low on CTRL fields and
freezes `lfsr_q` while exercising EVENTS so random hw loads do not race AXI
traffic.

Checks:

1. Read `CTRL` at `0x00` (reset value `0x2`)
2. Write/read `CTRL` (`0x5`)
3. Seed `EVENTS.pending` at `0x04`, read back `0xF`
4. AXI write `0x5` to `EVENTS` and verify `rw1c` clear → `0xA`

`EVENTS.pending` is seeded by forcing internal `events_q` (rw1c cannot set
pending bits via AXI write). The force is released before the rw1c write.

Simulation passes when the log contains `PASS: vcs_sim example-device`.

## external-device checks

Mirrors RTL behavior for internal, external, and write-only registers (not the
C-header mock store):

1. Load `STATUS.flag` via hw_access, read `0x1` at `0x00`
2. Write/read `FIFO` payload at `0x10`
3. Write/read `MEM` window at `0x20`
4. Read `ROM` slot 0 at `0x30` (harness reset image `0x1`)
5. Write `WBUF` at `0x40`, AXI read returns `0`, storage holds written data

Simulation passes when the log contains `PASS: vcs_sim external-device`.

## cca-accel checks

Uses `tests/testdata/cca_accel.md` (52-register DMA + accelerator map) and
the matching `quartus_sv_compile/cca-accel/csr_synth_harness.sv`. Mirrors the Simics
`cca-accel` snippet tests:

1. Read reset values for `WPREF_CONTROL`, `WDISP_STATUS`, `FPGA_ID`, `ACCEL_CONTROL`
2. Write/read `WPREF_CONTROL` RUN bit at `0x30204000`
3. Seed `WPREF_STATUS` IRQ, read `0x1`, release the force, then `rw1c` clear via AXI write

The testbench holds off harness LFSR `hw_access` loads during AXI checks.

Simulation passes when the log contains `PASS: vcs_sim cca-accel`.

## VCS and altera_axi4lite_mm_manager

VCS does not propagate `altera_axi4lite_mm_manager` clocking-block drives to
external AXI wires reliably. `test.sh` therefore patches a **local copy** of
`altera_lnsim.sv` under `<case>/work/` (never the Quartus install):

- Add `#1step` defaults to the lite manager `m_cb` clocking block
- Hold AR/AW address channels for one clock cycle before deasserting

The patch stamp is keyed by `PATCH_ID` (`vcs-skew-v2` in `common.sh`); changing
the patch logic bumps that ID so the work copy is regenerated.
