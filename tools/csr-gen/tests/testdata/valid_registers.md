# Device CSR Specification

Introductory prose may contain `|` characters without becoming a table.

## CSR Registers

| Description | Access | Reset | Bits | Field | Address | Register |
| --- | --- | --- | --- | --- | --- | --- |
| Control register | rw | 0x0 | 0 | enable | 0x00 | ctrl |
| Enable **debug** mode | rw | 0x1 | 2:1 | mode |  |  |
| Event register and pending bits | rw1c | 0x00 | 7:0 | pending | 0x04 | events |

### Notes

Nested headings remain part of the section.

# Other Section

Content after the CSR section is ignored.
