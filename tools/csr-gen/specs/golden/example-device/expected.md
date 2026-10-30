## CSR Registers

| Register | Address | Field | Bits | Access | Reset | HW Access | Description |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x0 |  |  |  |  | internal | Control register |
|  |  | ENABLE | 0 | rw | 0x0 |  | Control register |
|  |  | MODE | 2:1 | rw | 0x1 |  | Enable debug mode |
|  |  | RSVD | 31:3 | none | 0x0 |  | Select mode |
| EVENTS | 0x4 |  |  |  |  | internal | Event register and pending event bits |
|  |  | PENDING | 7:0 | rw1c | 0x0 |  | Event register and pending event bits |
