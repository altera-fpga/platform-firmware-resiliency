# Device

## CSR Registers

Introductory text for the whole block.

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x00 | enable | 0 | rw | 0x0 | Control |

### Event bank

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| EVENTS | 0x04 | pending | 7:0 | rw1c | 0x00 | Pending events |
