# Negative Golden CSR Specifications

Each subdirectory is an intentionally invalid Markdown CSR map. Tests load
`regs.md`, expect validation to fail, and match a fragment from `error.txt` in
the reported error list.

## Layout

```text
specs/golden-reject/<case-name>/
  regs.md
  section.txt
  error.txt
```

See `specs/golden/README.md` for positive examples.
