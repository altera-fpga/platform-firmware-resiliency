# Accellera SystemRDL 1.0 import tests

These tests import selected examples from
`tests/testdata/systemrdl/SystemRDL_1.0/Examples/` through the installed
`csr-gen` CLI and verify Markdown export plus `validate`.

Included cases (expected pass):

| Case | Source | Notes |
| --- | --- | --- |
| `counter-example` | `incr_cntr_test/counter_example.rdl` | Flat addrmap with counter field |
| `lock-and-key` | `lock_and_key/lock_and_key.rdl` | Field access gating example |
| `leon2-uart` | `Leon2/uart.rdl` | Leon2 UART peripheral (standalone addrmap) |
| `leon2-gpio` | `Leon2/gpio.rdl` | Leon2 GPIO peripheral |

Examples that require includes, preprocessors, or unsupported constructs
(`pci_example`, `hier_intrpt`, `sata_ahci`, and others) are intentionally
excluded. `generic_rdl/generic_example.rdl` is covered separately as an expected
failure in `test_accellera_generic_rdl.py` (signals, Perl preprocessing, `mem`).

Run via `make test-end2end-eda`.
