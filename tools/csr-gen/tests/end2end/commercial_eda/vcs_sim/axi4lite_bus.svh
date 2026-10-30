// Shared AXI4-Lite wires between altera_axi4lite_mm_manager (master) and csr_synth_harness (slave).
// Included inside csr_sim_tb; requires localparams ADDR_WIDTH and DATA_WIDTH.

    logic [ADDR_WIDTH-1:0] axi_awaddr;
    logic [2:0]            axi_awprot;
    logic                  axi_awvalid;
    logic                  axi_awready;
    logic [DATA_WIDTH-1:0] axi_wdata;
    logic [3:0]            axi_wstrb;
    logic                  axi_wvalid;
    logic                  axi_wready;
    logic [1:0]            axi_bresp;
    logic                  axi_bvalid;
    logic                  axi_bready;
    logic [ADDR_WIDTH-1:0] axi_araddr;
    logic [2:0]            axi_arprot;
    logic                  axi_arvalid;
    logic                  axi_arready;
    logic [DATA_WIDTH-1:0] axi_rdata;
    logic [1:0]            axi_rresp;
    logic                  axi_rvalid;
    logic                  axi_rready;
