# Example Device CSR Specification

Introductory prose may contain `|` characters without becoming a table.

## CSR Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x00 | enable | 0 | rw | 0x0 | Control register |
|  |  | mode | 2:1 | rw | 0x1 | Enable **debug** mode |
|  |  | rsvd | 31:3 | none | 0x0 | Select `<b>mode</b>` |
| EVENTS | 0x04 | pending | 7:0 | rw1c | 0x00 | Event register and pending event bits |

### Notes

Nested headings remain part of the section.

# Other Section

Content after the CSR section is ignored.
