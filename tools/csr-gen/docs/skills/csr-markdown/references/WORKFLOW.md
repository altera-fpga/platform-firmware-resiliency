# Authoring workflow

## 1. Interview

Collect enough to fill one named Markdown section:

1. **File path** for the CSR spec (new file or existing `.md`).
2. **Section heading** the user will pass to `--markdown-section` (for example
   `CSR Registers`). Confirm it appears once in the document.
3. **Registers:** name, byte offset (or range), software `Access` per field,
   reset, description, and whether the register is `internal` or `external`.
4. **Fields:** name, bit range (`N` or `M:N` with M ≥ N), access, reset.
5. **Ranges:** any window that is not a single 32-bit register (must be
   `external` with one `31:0` field).

If the user has prose notes, spreadsheets, or RTL comments, extract a table;
do not leave registers only in those sources.

## 2. Write Markdown

1. Open or create the target `.md` file.
2. Add or reuse the agreed heading.
3. Write a GitHub-flavored Markdown table. Prefer canonical columns and a
   **register definition row** before field rows.
4. Copy structure from [assets/template.md](../assets/template.md). For a
   small complete map, see [assets/example-device.md](../assets/example-device.md).
5. Keep other prose (intro, notes) outside the table cells as needed.

Read [TABLE_RULES.md](TABLE_RULES.md) before treating the file as done.

## 3. Validate

If `csr-gen` is on `PATH`:

```sh
csr-gen validate \
  --input-format markdown \
  --input-file <path-to.md> \
  --markdown-section "<heading>"
```

Fix every reported error in one pass; the tool does not emit a model until the
map is legal.

If `csr-gen` is **not** installed, check the table against TABLE_RULES.md and
tell the user the file is **unvalidated** until they run `csr-gen validate`.
Tell them to download the `csr_gen-*-py3-none-any.whl` asset from the latest
release at
<https://github.com/altera-fpga/platform-firmware-resiliency/releases> and run
`pip install` on that file. Do not install it for them.

## 4. Generate (optional)

Only if the user asked for artifacts and `csr-gen` is available. Markdown stays
authoritative; regenerate outputs instead of hand-editing them.

```sh
csr-gen generate \
  --input-file <path-to.md> \
  --input-format markdown \
  --markdown-section "<heading>" \
  --output-file <out.sv> \
  --output-format systemverilog
```

This skill does **not** cover IP-XACT/SystemRDL import, GUI usage, or bus
types other than documenting that AXI4-Lite is the current SystemVerilog
default.
