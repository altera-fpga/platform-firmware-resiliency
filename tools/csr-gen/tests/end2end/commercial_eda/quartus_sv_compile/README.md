# Quartus SystemVerilog compile tests

Each case synthesizes generated `csr_registers` RTL plus a checked-in
`csr_synth_harness.sv` using Quartus (`quartus_syn test -c test`). Warnings and
critical warnings in `output_files/test.syn.rpt` are treated as errors.

The harness top level exposes only clock, reset, the AXI4-Lite slave, and
`reg_obs`. Internal `hw_access` register field ports are wired inside the harness
(LFSR-driven `_d`/`_d_wen` and XOR on `_q` for internal fields; embedded SRAM for external registers). External register
interfaces connect to embedded SRAM models inside the harness and are not module
ports.

## Layout

```text
quartus_sv_compile/
  .gitignore              # Shared: Quartus outputs and generated csr_registers.sv
  <case>/
    test.qpf / test.qsf     # Quartus project (TOP_LEVEL_ENTITY csr_synth_harness)
    csr_synth_harness.sv    # Checked-in synthesizable harness (regenerate below)
    ignored_syn_messages.txt  # Optional; line-prefix allowlist for report §14 messages
    section.txt             # Optional; else specs/golden/<case>/section.txt
    test.sh                 # Manual / pytest entry point
    csr_registers.sv        # Generated each run (gitignored)
    output_files/ qdb/ dni/  # Quartus outputs (gitignored; removed each run)
```

Generated artifacts under each case directory are ignored via the shared
`.gitignore` in this directory; new cases do not need their own.

`syn_report_check.py` counts `Error`, `Critical Warning`, and `Warning` lines
in the **Synthesis Messages** section (report §14). Each line
`Severity (message_id): …` is one message; indented nested warnings are counted
separately. Legacy `; Warnings: N` lines are used only when that section is
absent.

On each run it prints:

```text
Warnings: <total> (<ignored> ignored)
Critical warnings: <total> (<ignored> ignored)
Errors: <count>
```

Pass policy: zero **effective** warnings and critical warnings (total minus ignored
prefixes) and zero errors.

Each case may provide `ignored_syn_messages.txt`: one message prefix per line
(blank lines and `#` comments allowed). A synthesis message is ignored when its
line in report §14 starts with a listed prefix (leading whitespace in the report
is ignored). Example:

```text
Warning (13410): Pin "s_axi_bresp[0]" is stuck at GND
```

matches:

```text
    Warning (13410): Pin "s_axi_bresp[0]" is stuck at GND File: ... Line: 18
```

**Do not widen the allowlist casually.** Each ignored prefix hides a real
synthesis finding. Prefer fixing generated RTL or the checked-in harness so the
warning goes away. Add or change entries in `ignored_syn_messages.txt` only when
a warning is genuinely expected for that harness (for example, known stuck-at
pins on unused AXI response bits in a synthesis-only smoke test).

**Agents:** do **not** edit `ignored_syn_messages.txt` automatically. If a run
fails the report check and the fix is not obvious RTL or harness work, stop and
ask the user whether to add ignore prefixes. The user must review and approve
any change to the allowlist before it is committed.

## Debugging a failed run

1. Run `tests/end2end/commercial_eda/quartus_sv_compile/<case>/test.sh` (requires
   `quartus_syn` and `csr-gen` on `PATH`).
2. On failure, open `output_files/test.syn.rpt`:
   - Section **12** — warnings attributed to harness/RTL sources
   - Section **13** — general warnings (device / flow)
   - Section **14** — full message text
3. Fix RTL or harness, regenerate `csr_synth_harness.sv` if needed, re-run.
4. If warnings remain and are expected for the harness, propose updates to
   `ignored_syn_messages.txt` for **user review** — do not commit allowlist
   changes without explicit approval.

Agents: after changing synthesis harness code, run `test.sh` when `quartus_syn`
is available; if it fails, inspect `output_files/test.syn.rpt` before guessing.
Fix RTL and harness first. Never add or edit `ignored_syn_messages.txt` on your
own; escalate to the user when the allowlist may need to change.

## Regenerate csr_synth_harness.sv

```bash
python scripts/generate_synth_test_harness.py tests/end2end/commercial_eda/quartus_sv_compile/example-device
python scripts/generate_synth_test_harness.py tests/end2end/commercial_eda/quartus_sv_compile/external-device
python scripts/generate_synth_test_harness.py <case-dir> --check   # CI drift check
```

## Run

After `make install`, the Makefile prepends `work/csr-gen/bin` to `PATH` so
`csr-gen` is available to test scripts. Quartus (`quartus_syn`) is freely
available; install it and put it on `PATH`:

```bash
make test-end2end-commercial-eda
tests/end2end/commercial_eda/quartus_sv_compile/example-device/test.sh
```

The pytest wrapper fails fast if `quartus_syn` is not on `PATH`.

## Quartus port style

With `` `default_nettype none ``, Quartus requires explicit net types on inputs:
use `input wire` (not `input logic` or `input wire logic`).
