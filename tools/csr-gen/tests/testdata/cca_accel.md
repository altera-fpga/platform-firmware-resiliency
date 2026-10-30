# CSR Registers

## DMA Registers

### Write Prefetcher CSR Block

Base Address: 0x3020_4000

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| WPREF_CONTROL | 0x30204000 | | | | | | Prefetcher control register |
| | | IRQ_EN | 3 | rw | 0x0 | |
| | | RESET | 2 | rw | 0x0 | |
| | | RESERVED | 1 | none | 0x0 | |
| | | RUN | 0 | rw | 0x0 | Self-clearing |
| WPREF_NEXT_DESC_LOW | 0x30204004 | DATA | 31:0 | rw | 0x0 | Next descriptor pointer [31:0] |
| WPREF_NEXT_DESC_HI | 0x30204008 | DATA | 31:0 | rw | 0x0 | Next descriptor pointer [63:32] |
| WPREF_RESERVED_0C | 0x3020400C | GAP | 31:0 | none | 0x0 | Reserved |
| WPREF_STATUS | 0x30204010 | | | | | | Status register (write-1-to-clear) |
| | | IRQ | 0 | rw1c | 0x0 | Transfer done |
| WPREF_DESC_POLL_FREQ | 0x30204014 | FREQ | 31:0 | rw | 0x0 | Descriptor polling frequency |
| WPREF_RESERVED_18 | 0x30204018 | GAP | 31:0 | none | 0x0 | Reserved |
| WPREF_RESERVED_1C | 0x3020401C | GAP | 31:0 | none | 0x0 | Reserved |

### Read Prefetcher CSR Block

Base Address: 0x3020_4020

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| RPREF_CONTROL | 0x30204020 | | | | | | Prefetcher control register |
| | | IRQ_EN | 3 | rw | 0x0 | |
| | | RESET | 2 | rw | 0x0 | |
| | | RESERVED | 1 | none | 0x0 | |
| | | RUN | 0 | rw | 0x0 | Self-clearing |
| RPREF_NEXT_DESC_LOW | 0x30204024 | DATA | 31:0 | rw | 0x0 | Next descriptor pointer [31:0] |
| RPREF_NEXT_DESC_HI | 0x30204028 | DATA | 31:0 | rw | 0x0 | Next descriptor pointer [63:32] |
| RPREF_RESERVED_0C | 0x3020402C | GAP | 31:0 | none | 0x0 | Reserved |
| RPREF_STATUS | 0x30204030 | | | | | | Status register (write-1-to-clear) |
| | | IRQ | 0 | rw1c | 0x0 | Transfer done |
| RPREF_DESC_POLL_FREQ | 0x30204034 | FREQ | 31:0 | rw | 0x0 | Descriptor polling frequency |
| RPREF_RESERVED_18 | 0x30204038 | GAP | 31:0 | none | 0x0 | Reserved |
| RPREF_RESERVED_1C | 0x3020403C | GAP | 31:0 | none | 0x0 | Reserved |

### Write Dispatcher CSR Block

Base Address: 0x3020_4040

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| WDISP_STATUS | 0x30204040 | | | | | | Dispatcher status register |
| | | RESET_IN_PROGRESS | 6 | ro | 0x0 | |
| | | STOPPED | 5 | ro | 0x0 | |
| | | RESETTING | 4 | ro | 0x0 | |
| | | STOPPED_ON_ERROR | 3 | ro | 0x0 | |
| | | RESP_BUF_FULL | 2 | ro | 0x0 | |
| | | STOPPED_IDLE | 1 | ro | 0x1 | Idle (normal reset state) |
| | | BUSY | 0 | ro | 0x0 | |
| WDISP_CONTROL | 0x30204044 | | | | | | Dispatcher control register |
| | | STOP_ON_EARLY_TERM | 4 | rw | 0x0 | |
| | | STOP_ON_ERROR | 3 | rw | 0x0 | |
| | | STOP_DESCRIPTORS | 2 | rw | 0x0 | |
| | | RESET | 1 | rw | 0x0 | |
| | | STOP | 0 | rw | 0x0 | |
| WDISP_FILL_LEVEL | 0x30204048 | LEVEL | 31:0 | ro | 0x0 | Descriptor buffer fill level |
| WDISP_RESPONSE_FILL_LEVEL | 0x3020404C | LEVEL | 31:0 | ro | 0x0 | Response buffer fill level |
| WDISP_SEQUENCE_NUMBER | 0x30204050 | NUMBER | 31:0 | ro | 0x0 | Current sequence number |
| WDISP_RESERVED_14 | 0x30204054 | GAP | 31:0 | none | 0x0 | Reserved |
| WDISP_RESERVED_18 | 0x30204058 | GAP | 31:0 | none | 0x0 | Reserved |
| WDISP_RESERVED_1C | 0x3020405C | GAP | 31:0 | none | 0x0 | Reserved |

Note: Dispatcher STATUS reset value = 0x02 (STOPPED_IDLE=1, BUSY=0) is the normal idle state.
Software should not modify dispatcher registers — the dispatcher is auto-managed by the prefetcher.

### Read Dispatcher CSR Block

Base Address: 0x3020_4060

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| RDISP_STATUS | 0x30204060 | | | | | | Dispatcher status register |
| | | RESET_IN_PROGRESS | 6 | ro | 0x0 | |
| | | STOPPED | 5 | ro | 0x0 | |
| | | RESETTING | 4 | ro | 0x0 | |
| | | STOPPED_ON_ERROR | 3 | ro | 0x0 | |
| | | RESP_BUF_FULL | 2 | ro | 0x0 | |
| | | STOPPED_IDLE | 1 | ro | 0x1 | Idle (normal reset state) |
| | | BUSY | 0 | ro | 0x0 | |
| RDISP_CONTROL | 0x30204064 | | | | | | Dispatcher control register |
| | | STOP_ON_EARLY_TERM | 4 | rw | 0x0 | |
| | | STOP_ON_ERROR | 3 | rw | 0x0 | |
| | | STOP_DESCRIPTORS | 2 | rw | 0x0 | |
| | | RESET | 1 | rw | 0x0 | |
| | | STOP | 0 | rw | 0x0 | |
| RDISP_FILL_LEVEL | 0x30204068 | LEVEL | 31:0 | ro | 0x0 | Descriptor buffer fill level |
| RDISP_RESPONSE_FILL_LEVEL | 0x3020406C | LEVEL | 31:0 | ro | 0x0 | Response buffer fill level |
| RDISP_SEQUENCE_NUMBER | 0x30204070 | NUMBER | 31:0 | ro | 0x0 | Current sequence number |
| RDISP_RESERVED_14 | 0x30204074 | GAP | 31:0 | none | 0x0 | Reserved |
| RDISP_RESERVED_18 | 0x30204078 | GAP | 31:0 | none | 0x0 | Reserved |
| RDISP_RESERVED_1C | 0x3020407C | GAP | 31:0 | none | 0x0 | Reserved |

Note: Dispatcher STATUS reset value = 0x02 (STOPPED_IDLE=1, BUSY=0) is the normal idle state.
Software should not modify dispatcher registers — the dispatcher is auto-managed by the prefetcher.

## Accelerator CSR Block

Base Address: 0x3040_0000

### FPGA Identification Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| FPGA_ID | 0x30400000 | | | | | | FPGA design identifier |
| | | MAJOR_ID | 31:24 | ro | 0x01 | Major design ID |
| | | MINOR_ID | 23:16 | ro | 0x01 | Minor design ID |
| | | RESERVED | 15:8 | none | 0x00 | Reserved |
| | | VARIANT_ID | 7:0 | ro | 0x03 | Variant / instance ID |
| FPGA_REVISION | 0x30400004 | | | | | | FPGA revision number |
| | | MAJOR_REL | 31:24 | ro | 0x01 | Major release number |
| | | MINOR_REL | 23:16 | ro | 0x01 | Minor release number |
| | | FPGA_REL | 15:8 | ro | 0x00 | FPGA build release |
| | | PATCH_REL | 7:0 | ro | 0x01 | Patch / hotfix release |
| RESERVED_08 | 0x30400008 | DATA | 31:0 | ro | 0x08080808 | Reserved — fixed pattern for verification |
| RESERVED_0C | 0x3040000C | DATA | 31:0 | ro | 0x0C0C0C0C | Reserved — fixed pattern for verification |

### Accelerator Control and Status Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| ACCEL_CONTROL | 0x30400010 | | | | | | Accelerator control register (reset default=RESET) |
| | | RESET | 15 | rw | 0x1 | Self-clearing, extends 3 cycles |
| | | RESERVED_14_11 | 14:11 | none | 0x0 | |
| | | ABORT | 10 | rw | 0x0 | |
| | | STOP | 9 | rw | 0x0 | |
| | | START | 8 | rw | 0x0 | Self-clearing |
| | | CMD | 7:0 | rw | 0x0 | 0x00=NOP, 0x01=PROCESS_DATA, 0x02=PASS_THROUGH, 0xFF=ERROR_TEST |
| ACCEL_STATUS | 0x30400014 | | | | | | Accelerator status register |
| | | ACCEL_ERROR | 4 | ro | 0x0 | |
| | | ACCEL_DONE | 3 | ro | 0x0 | |
| | | ACCEL_BUSY | 2 | ro | 0x0 | |
| | | ACCEL_ALIVE | 1 | ro | 0x0 | Toggles ~100ms @ 200MHz |
| | | ACCEL_ALIVE_FLAG | 0 | ro | 0x0 | Set once alive seen |
| RESERVED_18 | 0x30400018 | DATA | 31:0 | ro | 0x18181818 | Reserved — fixed pattern for verification |
| RESERVED_1C | 0x3040001C | DATA | 31:0 | ro | 0x1C1C1C1C | Reserved — fixed pattern for verification |

### Debug and Test Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| ACCEL_DBG_TST_REG | 0x30400040 | DATA | 31:0 | rw | 0x0 | Debug test register |
| ACCEL_DBG_0_REG_DATA | 0x30400044 | DATA | 31:0 | rw | 0x0 | Debug data register 0 |
| ACCEL_DBG_1_REG_DATA | 0x30400048 | DATA | 31:0 | rw | 0x0 | Debug data register 1 |
| ACCEL_DBG_2_REG_DATA | 0x3040004C | DATA | 31:0 | rw | 0x0 | Debug data register 2 |
| ACCEL_DBG_3_REG_DATA | 0x30400050 | DATA | 31:0 | rw | 0x0 | Debug data register 3 |
| ACCEL_DBG_4_REG_DATA | 0x30400054 | DATA | 31:0 | rw | 0x0 | Debug data register 4 |
| ACCEL_DBG_5_REG_DATA | 0x30400058 | DATA | 31:0 | rw | 0x0 | Debug data register 5 |
| ACCEL_DBG_6_REG_DATA | 0x3040005C | DATA | 31:0 | rw | 0x0 | Debug data register 6 |
| ACCEL_DBG_7_REG_DATA | 0x30400060 | DATA | 31:0 | rw | 0x0 | Debug data register 7 |
| ACCEL_DBG_8_REG_DATA | 0x30400064 | DATA | 31:0 | rw | 0x0 | Debug data register 8 |
| ACCEL_DBG_9_REG_DATA | 0x30400068 | DATA | 31:0 | rw | 0x0 | Debug data register 9 |
| ACCEL_DBG_10_REG_DATA | 0x3040006C | DATA | 31:0 | rw | 0x0 | Debug data register 10 (firmware breadcrumb) |

Note: All Accelerator CSR registers accessed via Nios V at base address 0x30400000.
Full address = 0x30400000 + offset.
