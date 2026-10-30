# External Device CSR Specification

## CSR Registers

| Register | Address | Field | Bits | Access | Reset | Description | HW Access |
| --- | --- | --- | --- | --- | --- | --- | --- |
| STATUS | 0x00 | flag | 0 | ro | 0x0 | Device ready flag | internal |
| FIFO | 0x10 | data | 7:0 | rw | 0x0 | FIFO payload | external |
|  |  | level | 15:8 | ro | 0x0 | FIFO fill level | |
| MEM | 0x20-0x2F | window | 31:0 | rw | 0x0 | External read/write memory window | external |
| ROM | 0x30-0x3F | image | 31:0 | ro | 0x0 | External read-only memory window | external |
| WBUF | 0x40-0x4F | buffer | 31:0 | wo | 0x0 | External write-only memory window | external |
