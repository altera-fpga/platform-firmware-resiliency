# csr-gen Markdown table rules

Author Markdown that `csr-gen` can parse. Do not invent a second dialect.

Markdown is the source of truth. Do not treat YAML dumps, SystemVerilog, C
headers, DML, IP-XACT, or SystemRDL as the specification.

## Document and section

- Put the CSR table in a **named section**. The heading string is what the user
  will pass as `--markdown-section` (match is case-insensitive).
- The document must contain **exactly one** matching heading.
- That section may have one table in the section body and/or one table under
  each deeper subsection. All tables merge into one address map; legality checks
  apply across the whole section.
- Generated RTL and headers still cover the full block (one CSR, not one module
  per subsection).

## Columns

**Required:** `Register`, `Address`, `Field`, `Bits` (order and capitalization
may vary on input).

**Optional:** `Access`, `Description`, `HW Access`, `Reset`.

When **writing new files**, use canonical column order:

`Register`, `Address`, `Field`, `Bits`, `Access`, `Reset`, `HW Access`, `Description`

| Column | If omitted |
| --- | --- |
| `Access` | Defaults to `rw` |
| `Description` | Field name on field rows; register name on definition rows |
| `HW Access` | Defaults to `internal` on register definition or combined rows |
| `Reset` column | Every field reset is `0` |
| `Reset` cell (column present) | Not allowed; every row needs a reset value |

## Row kinds

- **Every data row must define a `Field`** except a **register definition row**.
- **Register definition row:** `Register` and `Address` filled; `Field`, `Bits`,
  `Access`, and `Reset` empty. Sets register description and `HW Access`. At
  least one **field row** must follow.
- **Combined row:** `Register`, `Address`, and first `Field` on one line. Valid
  input; one `Description` applies to both register and that field.
- **Field row:** empty `Register` and `Address`. Description applies to the
  field only. **`HW Access` must be empty** on field rows.

Prefer **definition-row-first** (what `csr-gen` writes on Markdown export).

## Addresses and widths

- Addresses are **byte offsets in the CSR block**, not system-level addresses.
- Registers are **32-bit** with **4-byte-aligned** offsets.
- Single offset (`0x10` or bare hex `10`) or inclusive range whose end is the
  last byte (`0x20-0x2F`, `0x8000-0x15FFFF`).
- Bare digit sequences are **base 16** (`10` means `0x10`).
- The byte count `(end - start + 1)` must be a multiple of four. Use ASCII `-`.
- Address **gaps** are legal. Full 32-bit field coverage is **not** required;
  undescribed bits are unimplemented.

## Names

- Letters, digits, and underscores only; must not start with a digit.
- `csr-gen` normalizes imported names to **uppercase**.

## Access (software)

| Key | Meaning |
| --- | --- |
| `none` | Reserved: reads return reset; writes ignored |
| `ro` | Read only |
| `rc` | Read only; reading clears |
| `rw` | Read/write |
| `r0w1c` | Read zero; write `1` clears |
| `rw1s` | Read; write `1` sets |
| `rw1c` | Read; write `1` clears |
| `rw0c` | Read; write `0` clears |
| `wo` | Write only |

## HW Access (hardware)

Applies to the **whole register**. Set only on a definition or combined row.

| Value | Meaning |
| --- | --- |
| `internal` | Storage and field logic inside the CSR module |
| `external` | AXI read/write delegated to external ports |

Address **ranges** require `HW Access` `external` and **exactly one** field on
bits `31:0`.

## Validation behavior

`csr-gen validate` collects every illegal row and does not build a model if any
error is present. Typical rejects: empty required cells, duplicate names or
addresses, overlapping fields (including `none`), invalid access, malformed
hex, reset values that do not fit the field, invalid `HW Access`, internal
registers with ranges, overlapping occupied byte offsets.
