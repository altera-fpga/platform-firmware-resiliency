# Examples

Walkthroughs of two bundled register maps and the outputs `csr-gen` produces
from each. **Markdown is the source of truth:** you document registers in
readable prose and tables, then generate RTL and headers from that spec. Use
the commands in each section with your own `regs.md` files by changing the
input paths.

## Generated outputs

From a Markdown CSR table, `csr-gen` can emit:

- **Normalized Markdown** — canonical register table with optional columns
  filled in (including `HW Access` when omitted in the source).
- **SystemVerilog** — AXI4-Lite slave wrapper, register map documentation,
  design-facing ports (`_q`, `_q_upd`, `_d`, and `_d_wen` for internal fields; additional
  handshake and address ports for external registers and ranges).
- **C header** — base address, per-register offsets, and field get/set macros
  for firmware.
- **Simics DML** — DML 1.4 device and bank for software simulation (field
  templates from `utility.dml`; ranged registers as arrays).

Bundled reference specs live under
[`specs/golden/`](../specs/golden/README.md).

## Example device (internal registers)

A small map with **internal** registers only. The author `regs.md` uses flexible column order, inline Markdown in cells, and extra prose around the table. `csr-gen` normalizes names, adds the `HW Access` column on export, and generates an AXI4-Lite slave with per-field `_q`, `_q_upd`, `_d`, and `_d_wen` ports.

Reference specification: [`specs/golden/example-device/`](../specs/golden/example-device)

### Commands

```sh
csr-gen validate \
  --input-file specs/golden/example-device/regs.md \
  --markdown-section "CSR Registers"

csr-gen generate \
  --input-file specs/golden/example-device/regs.md \
  --input-format markdown \
  --markdown-section "CSR Registers" \
  --output-file work/example-device.sv \
  --output-format systemverilog \
  --output-file work/example-device.h \
  --output-format c-header \
  --output-file work/example-device.dml \
  --output-format dml \
  --output-file work/example-device.normalized.md \
  --output-format markdown
```

### Author specification

The register map lives in human-readable Markdown—prose, headings, and tables—not in a separate machine-only format. Below is the bundled `regs.md` as you would author it (source) and as it appears when rendered.

#### Source

```markdown
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
```

#### Rendered

#### Example Device CSR Specification

Introductory prose may contain `|` characters without becoming a table.

##### CSR Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x00 | enable | 0 | rw | 0x0 | Control register |
|  |  | mode | 2:1 | rw | 0x1 | Enable **debug** mode |
|  |  | rsvd | 31:3 | none | 0x0 | Select `<b>mode</b>` |
| EVENTS | 0x04 | pending | 7:0 | rw1c | 0x00 | Event register and pending event bits |

###### Notes

Nested headings remain part of the section.

#### Other Section

Content after the CSR section is ignored.


### Normalized Markdown

Exported register table with optional columns filled in and explicit defaults (including `HW Access` when omitted in the source):

```markdown
## CSR Registers

| Register | Address | Field | Bits | Access | Reset | HW Access | Description |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x0 |  |  |  |  | internal | Control register |
|  |  | ENABLE | 0 | rw | 0x0 |  | Control register |
|  |  | MODE | 2:1 | rw | 0x1 |  | Enable debug mode |
|  |  | RSVD | 31:3 | none | 0x0 |  | Select mode |
| EVENTS | 0x4 |  |  |  |  | internal | Event register and pending event bits |
|  |  | PENDING | 7:0 | rw1c | 0x0 |  | Event register and pending event bits |
```

### SystemVerilog

Generated module includes an AXI4-Lite slave, a register map comment, design-facing ports, and per-register logic. Excerpts:

Register map:

```text
+----------+---------+---------------------------------------+
| Register | Address | Description                           |
+----------+---------+---------------------------------------+
| CTRL     | 0x00    | Control register                      |
| EVENTS   | 0x04    | Event register and pending event bits |
+----------+---------+---------------------------------------+
```

Design-side ports:

```systemverilog
    // Register interfaces
    // --- CTRL @ 0x00 ---
    output logic [2:1] ctrl_mode_q,
    output logic        ctrl_mode_q_upd,
    input  wire [2:1] ctrl_mode_d,
    input  wire        ctrl_mode_d_wen,
    output logic        ctrl_enable_q,
    output logic        ctrl_enable_q_upd,
    input  wire        ctrl_enable_d,
    input  wire        ctrl_enable_d_wen,
    // --- EVENTS @ 0x04 ---
    output logic [7:0] events_pending_q,
    output logic        events_pending_q_upd,
    input  wire [7:0] events_pending_d,
    input  wire        events_pending_d_wen
```

Sample register logic:

```systemverilog
    // --- CTRL @ 0x00 ---
    output logic [2:1] ctrl_mode_q,
    output logic        ctrl_mode_q_upd,
    input  wire [2:1] ctrl_mode_d,
    input  wire        ctrl_mode_d_wen,
    output logic        ctrl_enable_q,
    output logic        ctrl_enable_q_upd,
    input  wire        ctrl_enable_d,
    input  wire        ctrl_enable_d_wen,
    // --- EVENTS @ 0x04 ---
    output logic [7:0] events_pending_q,
    output logic        events_pending_q_upd,
    input  wire [7:0] events_pending_d,
    input  wire        events_pending_d_wen
);

    localparam int unsigned OFFSET_WIDTH = 4;

    // AXI4-Lite interface
    logic [3:0] s_axi_awaddr_r;
    logic [3:0] s_axi_araddr_r;
    logic        aw_pending;
    logic        ar_pending;
    logic        b_pending;
    logic [31:0] write_offset;
    logic [31:0] read_offset;
    logic        write_en;
    logic        read_en;
    logic [31:0] read_data;
    logic        write_ok;
    logic        read_ok;

    assign write_offset = {{28{1'b0}}, s_axi_awaddr_r} - BASE_ADDR;
    assign read_offset = {{28{1'b0}}, s_axi_araddr_r} - BASE_ADDR;

    // ...
```

### C header

Generated header provides base/offset addresses, field get/set macros, and a register map comment. Excerpts:

Register map:

```text
+----------+---------+---------------------------------------+
| Register | Address | Description                           |
+----------+---------+---------------------------------------+
| CTRL     | 0x00    | Control register                      |
| EVENTS   | 0x04    | Event register and pending event bits |
+----------+---------+---------------------------------------+
```

Address and field macros:

```c
#define CSR_REGISTERS_BASE_ADDR 0x00000000u
#define CSR_REGISTERS_CTRL_ADDR (CSR_REGISTERS_CTRL_OFFSET + CSR_REGISTERS_BASE_ADDR)
#define CSR_REGISTERS_CTRL_ENABLE_GET(reg) \
#define CSR_REGISTERS_CTRL_ENABLE_SET(reg, val) \
#define CSR_REGISTERS_CTRL_MODE_GET(reg) \
#define CSR_REGISTERS_CTRL_MODE_SET(reg, val) \
#define CSR_REGISTERS_EVENTS_ADDR (CSR_REGISTERS_EVENTS_OFFSET + CSR_REGISTERS_BASE_ADDR)
#define CSR_REGISTERS_EVENTS_PENDING_GET(reg) \
#define CSR_REGISTERS_EVENTS_PENDING_SET(reg, val) \
```

### Simics DML

Generated DML describes a Simics 1.4 device and bank using `utility.dml` field templates. Ranged external registers become array declarations. Excerpts:

Register map:

```text
+----------+---------+---------------------------------------+
| Register | Address | Description                           |
+----------+---------+---------------------------------------+
| CTRL     | 0x00    | Control register                      |
| EVENTS   | 0x04    | Event register and pending event bits |
+----------+---------+---------------------------------------+
```

Sample register declarations:

```dml
    // --- CTRL @ 0x0 ---
    register CTRL size 4 @ 0x0 {
        // Control register
        field RSVD @ [31:3] is (reserved) {
            // Select mode
            param init_val = 0x0;
        }
        field MODE @ [2:1] is (read, write) {
            // Enable debug mode
            param init_val = 0x1;
        }
        field ENABLE @ [0] is (read, write) {
            // Control register
            param init_val = 0x0;
        }
    }
```

### Complete output files

- [`regs.md`](../specs/golden/example-device/regs.md) — Markdown specification you author
- [`expected.md`](../specs/golden/example-device/expected.md) — normalized Markdown table export
- [`expected.sv`](../specs/golden/example-device/expected.sv) — complete AXI4-Lite SystemVerilog module
- [`expected.h`](../specs/golden/example-device/expected.h) — complete C register header
- [`expected.dml`](../specs/golden/example-device/expected.dml) — complete Simics DML 1.4 device

## External device (delegated registers and ranges)

Shows **external** registers: a mixed FIFO register, and inclusive address ranges (`0x20-0x2F`) with a single `31:0` field for memory-style windows. RTL exposes `_wren`, `_rden`, `_wstrb`, `_wdata`, `_rdata`, `_rdatavalid`, and `_waddr` / `_raddr` on ranged externals.

Reference specification: [`specs/golden/external-device/`](../specs/golden/external-device)

### Commands

```sh
csr-gen validate \
  --input-file specs/golden/external-device/regs.md \
  --markdown-section "CSR Registers"

csr-gen generate \
  --input-file specs/golden/external-device/regs.md \
  --input-format markdown \
  --markdown-section "CSR Registers" \
  --output-file work/external-device.sv \
  --output-format systemverilog \
  --output-file work/external-device.h \
  --output-format c-header \
  --output-file work/external-device.dml \
  --output-format dml \
  --output-file work/external-device.normalized.md \
  --output-format markdown
```

### Author specification

The register map lives in human-readable Markdown—prose, headings, and tables—not in a separate machine-only format. Below is the bundled `regs.md` as you would author it (source) and as it appears when rendered.

#### Source

```markdown
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
```

#### Rendered

#### External Device CSR Specification

##### CSR Registers

| Register | Address | Field | Bits | Access | Reset | Description | HW Access |
| --- | --- | --- | --- | --- | --- | --- | --- |
| STATUS | 0x00 | flag | 0 | ro | 0x0 | Device ready flag | internal |
| FIFO | 0x10 | data | 7:0 | rw | 0x0 | FIFO payload | external |
|  |  | level | 15:8 | ro | 0x0 | FIFO fill level | |
| MEM | 0x20-0x2F | window | 31:0 | rw | 0x0 | External read/write memory window | external |
| ROM | 0x30-0x3F | image | 31:0 | ro | 0x0 | External read-only memory window | external |
| WBUF | 0x40-0x4F | buffer | 31:0 | wo | 0x0 | External write-only memory window | external |


### Normalized Markdown

Exported register table with optional columns filled in and explicit defaults (including `HW Access` when omitted in the source):

```markdown
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
```

### SystemVerilog

Generated module includes an AXI4-Lite slave, a register map comment, design-facing ports, and per-register logic. Excerpts:

Register map:

```text
+----------+-----------+-----------------------------------+
| Register | Address   | Description                       |
+----------+-----------+-----------------------------------+
| STATUS   | 0x00      | Device ready flag                 |
| FIFO     | 0x10      | FIFO payload                      |
| MEM      | 0x20-0x2F | External read/write memory window |
| ROM      | 0x30-0x3F | External read-only memory window  |
| WBUF     | 0x40-0x4F | External write-only memory window |
+----------+-----------+-----------------------------------+
```

Design-side ports:

```systemverilog
    // Register interfaces
    // --- STATUS @ 0x00 ---
    input  wire        status_flag_d,
    input  wire        status_flag_d_wen,
    // --- FIFO @ 0x10 ---
    output logic        fifo_wren,
    output logic [31:0] fifo_wdata,
    output logic [ 3:0] fifo_wstrb,
    output logic        fifo_rden,
    input  wire [31:0] fifo_rdata,
    input  wire        fifo_rdatavalid,
    // --- MEM @ 0x20-0x2F ---
    output logic        mem_wren,
    output logic [31:0] mem_wdata,
    output logic [ 3:0] mem_wstrb,
    output logic [1:0] mem_waddr,
    output logic        mem_rden,
    input  wire [31:0] mem_rdata,
    input  wire        mem_rdatavalid,
    output logic [1:0] mem_raddr,
    // --- ROM @ 0x30-0x3F ---
    output logic        rom_rden,
    input  wire [31:0] rom_rdata,
    input  wire        rom_rdatavalid,
    output logic [1:0] rom_raddr,
    // --- WBUF @ 0x40-0x4F ---
    output logic        wbuf_wren,
    output logic [31:0] wbuf_wdata,
    output logic [ 3:0] wbuf_wstrb,
    output logic [1:0] wbuf_waddr
```

Sample register logic:

```systemverilog
    // --- FIFO @ 0x10 ---
    output logic        fifo_wren,
    output logic [31:0] fifo_wdata,
    output logic [ 3:0] fifo_wstrb,
    output logic        fifo_rden,
    input  wire [31:0] fifo_rdata,
    input  wire        fifo_rdatavalid,
    // --- MEM @ 0x20-0x2F ---
    output logic        mem_wren,
    output logic [31:0] mem_wdata,
    output logic [ 3:0] mem_wstrb,
    output logic [1:0] mem_waddr,
    output logic        mem_rden,
    input  wire [31:0] mem_rdata,
    input  wire        mem_rdatavalid,
    output logic [1:0] mem_raddr,
    // --- ROM @ 0x30-0x3F ---
    output logic        rom_rden,
    input  wire [31:0] rom_rdata,
    input  wire        rom_rdatavalid,
    output logic [1:0] rom_raddr,
    // --- WBUF @ 0x40-0x4F ---
    output logic        wbuf_wren,
    output logic [31:0] wbuf_wdata,
    output logic [ 3:0] wbuf_wstrb,
    output logic [1:0] wbuf_waddr
);

    localparam int unsigned OFFSET_WIDTH = 7;

    // AXI4-Lite interface
    logic [6:0] s_axi_awaddr_r;
    logic [6:0] s_axi_araddr_r;
    logic        aw_pending;
    logic        ar_pending;
    // ...
```

### C header

Generated header provides base/offset addresses, field get/set macros, and a register map comment. Excerpts:

Register map:

```text
+----------+-----------+-----------------------------------+
| Register | Address   | Description                       |
+----------+-----------+-----------------------------------+
| STATUS   | 0x00      | Device ready flag                 |
| FIFO     | 0x10      | FIFO payload                      |
| MEM      | 0x20-0x2F | External read/write memory window |
| ROM      | 0x30-0x3F | External read-only memory window  |
| WBUF     | 0x40-0x4F | External write-only memory window |
+----------+-----------+-----------------------------------+
```

Address and field macros:

```c
#define CSR_REGISTERS_BASE_ADDR 0x00000000u
#define CSR_REGISTERS_STATUS_ADDR (CSR_REGISTERS_STATUS_OFFSET + CSR_REGISTERS_BASE_ADDR)
#define CSR_REGISTERS_STATUS_FLAG_GET(reg) \
#define CSR_REGISTERS_STATUS_FLAG_SET(reg, val) \
#define CSR_REGISTERS_FIFO_ADDR (CSR_REGISTERS_FIFO_OFFSET + CSR_REGISTERS_BASE_ADDR)
#define CSR_REGISTERS_FIFO_DATA_GET(reg) \
#define CSR_REGISTERS_FIFO_DATA_SET(reg, val) \
#define CSR_REGISTERS_FIFO_LEVEL_GET(reg) \
#define CSR_REGISTERS_FIFO_LEVEL_SET(reg, val) \
#define CSR_REGISTERS_MEM_ADDR (CSR_REGISTERS_MEM_OFFSET + CSR_REGISTERS_BASE_ADDR)
#define CSR_REGISTERS_MEM_WINDOW_GET(reg) \
#define CSR_REGISTERS_MEM_WINDOW_SET(reg, val) \
```

### Simics DML

Generated DML describes a Simics 1.4 device and bank using `utility.dml` field templates. Ranged external registers become array declarations. Excerpts:

Register map:

```text
+----------+-----------+-----------------------------------+
| Register | Address   | Description                       |
+----------+-----------+-----------------------------------+
| STATUS   | 0x00      | Device ready flag                 |
| FIFO     | 0x10      | FIFO payload                      |
| MEM      | 0x20-0x2F | External read/write memory window |
| ROM      | 0x30-0x3F | External read-only memory window  |
| WBUF     | 0x40-0x4F | External write-only memory window |
+----------+-----------+-----------------------------------+
```

Sample register declarations:

```dml
    // --- MEM @ 0x20-0x2F ---
    register MEM[i < 4] @ (0x20 + i * 4) is (read, write) "External read/write memory window";
```

### Complete output files

- [`regs.md`](../specs/golden/external-device/regs.md) — Markdown specification you author
- [`expected.md`](../specs/golden/external-device/expected.md) — normalized Markdown table export
- [`expected.sv`](../specs/golden/external-device/expected.sv) — complete AXI4-Lite SystemVerilog module
- [`expected.h`](../specs/golden/external-device/expected.h) — complete C register header
- [`expected.dml`](../specs/golden/external-device/expected.dml) — complete Simics DML 1.4 device

## See also

- [README](../README.md) — installation, CLI usage, and register table rules
