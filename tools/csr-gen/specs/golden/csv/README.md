# Golden CSV CSR Specifications

CSV golden cases mirror [`../README.md`](../README.md) Markdown goldens: each
subdirectory is one register map with semantic and export oracles.

## Layout

```text
specs/golden/csv/<case-name>/
  regs.csv        # Author-style input (combined rows for case 1)
  expected.csv    # Canonical CSV export (register definition rows + field rows)
  model.yml       # Normalized register model (same semantics as Markdown golden)
  csr-name.txt    # Optional label for export (--csr-name); tests read when present
```

## Cases

| Case | `regs.csv` shape | Purpose |
| --- | --- | --- |
| `example-device` | Combined register + first field per row | Legacy import path (like `specs/golden/example-device/regs.md`) |
| `example-device-canonical` | Split register-definition + field rows | Canonical export shape as author input; round-trip oracle |

Share `model.yml` semantics with `specs/golden/example-device/`.

## Tests

`tests/unittests/test_golden_csv_specs.py` discovers every case directory
automatically.

## Regenerating `expected.csv`

```python
from pathlib import Path
from csr_gen.input.yaml_reader import load_yaml_file
from csr_gen.output.csv_writer import write_csv_file

case = Path("specs/golden/csv/example-device")
model = load_yaml_file(case / "model.yml")
write_csv_file(case / "expected.csv", model)
```

Copy `expected.csv` to `example-device-canonical/regs.csv` when updating the
canonical case.
