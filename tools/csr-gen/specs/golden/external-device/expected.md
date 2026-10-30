## CSR Registers

| Register | Address | Field | Bits | Access | Reset | HW Access | Description |
| --- | --- | --- | --- | --- | --- | --- | --- |
| STATUS | 0x0 |  |  |  |  | internal | Device ready flag |
|  |  | FLAG | 0 | ro | 0x0 |  | Device ready flag |
| FIFO | 0x10 |  |  |  |  | external | FIFO payload |
|  |  | DATA | 7:0 | rw | 0x0 |  | FIFO payload |
|  |  | LEVEL | 15:8 | ro | 0x0 |  | FIFO fill level |
| MEM | 0x20-0x2f |  |  |  |  | external | External read/write memory window |
|  |  | WINDOW | 31:0 | rw | 0x0 |  | External read/write memory window |
| ROM | 0x30-0x3f |  |  |  |  | external | External read-only memory window |
|  |  | IMAGE | 31:0 | ro | 0x0 |  | External read-only memory window |
| WBUF | 0x40-0x4f |  |  |  |  | external | External write-only memory window |
|  |  | BUFFER | 31:0 | wo | 0x0 |  | External write-only memory window |
