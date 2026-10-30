# PeakRDL end-to-end smoke tests

These tests validate that golden oracles under `specs/golden/` compile through the
PeakRDL toolchain:

- `peakrdl html` — documentation generation from golden `expected.rdl`
- `peakrdl regblock` — SystemVerilog CSR block elaboration from golden `expected.rdl`
- `peakrdl dump` — IP-XACT import and elaboration from golden `expected.xml`

They are **smoke tests only**. Generated PeakRDL RTL and HTML are not compared to
csr-gen SystemVerilog or C-header goldens.

## Requirements

Install EDA test dependencies into the dedicated end-to-end venv:

```sh
make test-end2end-eda
```

This reads `requirements-eda.txt` in addition to the normal test requirements
(including `peakrdl-ipxact`).
