# Device CSR Specification

Replace this prose with a short description of the peripheral. Keep the section
heading in sync with `--markdown-section`.

## CSR Registers

| Register | Address | Field | Bits | Access | Reset | HW Access | Description |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x00 |  |  |  |  | internal | Control register |
|  |  | ENABLE | 0 | rw | 0x0 |  | Master enable |
|  |  | MODE | 2:1 | rw | 0x0 |  | Operating mode |
| STATUS | 0x04 |  |  |  |  | internal | Status register |
|  |  | READY | 0 | ro | 0x0 |  | Device ready |
