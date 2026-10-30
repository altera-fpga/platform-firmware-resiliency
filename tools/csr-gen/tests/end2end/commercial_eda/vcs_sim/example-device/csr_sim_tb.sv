// Functional simulation testbench for example-device CSR RTL.
// Drives csr_synth_harness via Intel altera_axi4lite_mm_manager (Quartus sim_lib).
`timescale 1 ps / 1 ps
`default_nettype none

module csr_sim_tb;

    import altera_axi_bfm_pkg::*;

    localparam int unsigned ADDR_WIDTH = 32;
    localparam int unsigned DATA_WIDTH = 32;
    localparam int unsigned CLK_HALF_PERIOD_PS = 5000;

    logic clk;
    logic rst;
    logic rstn;

    assign rst = ~rstn;

    `include "axi4lite_bus.svh"

    altera_axi4lite_mm_manager #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .DATA_WIDTH(DATA_WIDTH)
    ) u_axi (
        .clk    (clk),
        .rstn   (rstn),
        .awaddr (axi_awaddr),
        .awprot (axi_awprot),
        .awvalid(axi_awvalid),
        .awready(axi_awready),
        .wdata  (axi_wdata),
        .wstrb  (axi_wstrb),
        .wvalid (axi_wvalid),
        .wready (axi_wready),
        .bresp  (axi_bresp),
        .bvalid (axi_bvalid),
        .bready (axi_bready),
        .araddr (axi_araddr),
        .arprot (axi_arprot),
        .arvalid(axi_arvalid),
        .arready(axi_arready),
        .rdata  (axi_rdata),
        .rresp  (axi_rresp),
        .rvalid (axi_rvalid),
        .rready (axi_rready)
    );

    csr_synth_harness u_dut (
        .clk           (clk),
        .rst           (rst),
        .s_axi_awaddr  (axi_awaddr),
        .s_axi_awvalid (axi_awvalid),
        .s_axi_awready (axi_awready),
        .s_axi_wdata   (axi_wdata),
        .s_axi_wstrb   (axi_wstrb),
        .s_axi_wvalid  (axi_wvalid),
        .s_axi_wready  (axi_wready),
        .s_axi_bresp   (axi_bresp),
        .s_axi_bvalid  (axi_bvalid),
        .s_axi_bready  (axi_bready),
        .s_axi_araddr  (axi_araddr),
        .s_axi_arvalid (axi_arvalid),
        .s_axi_arready (axi_arready),
        .s_axi_rdata   (axi_rdata),
        .s_axi_rresp   (axi_rresp),
        .s_axi_rvalid  (axi_rvalid),
        .s_axi_rready  (axi_rready),
        .reg_obs       ()
    );

    initial begin
        clk = 1'b0;
        forever #(CLK_HALF_PERIOD_PS) clk = ~clk;
    end

    initial begin
        rstn = 1'b0;
        #(CLK_HALF_PERIOD_PS * 4);
        repeat (4) @(posedge clk);
        rstn = 1'b1;
    end

    task automatic axi_write(
        BaseAxiBfm#(ADDR_WIDTH, DATA_WIDTH, ID_WIDTH, 32) mgr,
        input logic [31:0] addr,
        input logic [31:0] data
    );
        AlteraAxiTransaction tr;
        tr = mgr.manager_bfm_wr_tx(0, addr, data);
        mgr.put_transaction(tr);
        mgr.drive_transaction();
    endtask

    task automatic axi_read(
        BaseAxiBfm#(ADDR_WIDTH, DATA_WIDTH, ID_WIDTH, 32) mgr,
        input  logic [31:0] addr,
        output logic [31:0] data
    );
        AlteraAxiTransaction tr;
        tr = mgr.manager_bfm_rd_tx(0, addr);
        mgr.put_transaction(tr);
        mgr.drive_transaction();
        data = tr.rdata;
    endtask

    task automatic check_eq(
        input string       label,
        input logic [31:0] actual,
        input logic [31:0] expected,
        inout int          err_cnt
    );
        if (actual !== expected) begin
            err_cnt += 1;
            $display(
                "FAIL: %s expected 0x%08x got 0x%08x",
                label,
                expected,
                actual
            );
        end else begin
            $display("INFO: %s ok (0x%08x)", label, actual);
        end
    endtask

    initial begin
        BaseAxiBfm#(ADDR_WIDTH, DATA_WIDTH, ID_WIDTH, 32) axi_mgr_bfm;
        int err_cnt;
        logic [31:0] rdata_val;

        axi_mgr_bfm = u_axi.AXI4LITEMAN.bfm;
        err_cnt = 0;

        axi_mgr_bfm.m_reset();
        repeat (5) @(posedge clk);

        // Hold off LFSR hw_access updates on CTRL during AXI checks.
        force u_dut.dut.ctrl_mode_d_wen = 1'b0;
        force u_dut.dut.ctrl_enable_d_wen = 1'b0;

        axi_read(axi_mgr_bfm, 32'h0, rdata_val);
        check_eq("CTRL reset", rdata_val, 32'h0000_0002, err_cnt);

        axi_write(axi_mgr_bfm, 32'h0, 32'h0000_0005);
        axi_read(axi_mgr_bfm, 32'h0, rdata_val);
        check_eq("CTRL write/read", rdata_val, 32'h0000_0005, err_cnt);

        // Seed EVENTS.pending via internal register; LFSR hw_access is exercised
        // in synthesis harness but not needed to validate AXI rw1c behavior.
        force u_dut.lfsr_q = 14'h0000;
        force u_dut.dut.events_q = 32'h0000_000f;
        repeat (2) @(posedge clk);

        axi_read(axi_mgr_bfm, 32'h4, rdata_val);
        check_eq("EVENTS hw load", rdata_val, 32'h0000_000f, err_cnt);

        release u_dut.dut.events_q;
        force u_dut.dut.events_pending_d_wen = 1'b0;
        repeat (1) @(posedge clk);

        axi_write(axi_mgr_bfm, 32'h4, 32'h0000_0005);
        axi_read(axi_mgr_bfm, 32'h4, rdata_val);
        check_eq("EVENTS rw1c clear", rdata_val, 32'h0000_000a, err_cnt);

        release u_dut.lfsr_q;

        if (err_cnt == 0) begin
            $display("PASS: vcs_sim example-device");
        end else begin
            $display("FAIL: vcs_sim example-device (%0d mismatches)", err_cnt);
        end
        $finish;
    end

    initial begin
        #(CLK_HALF_PERIOD_PS * 200000);
        $display("FAIL: simulation timeout");
        $finish;
    end

endmodule
