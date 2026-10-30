import stest
import csr_registers_common

dev = csr_registers_common.create_csr_registers()
regs = csr_registers_common.Registers(dev)
bank = regs.bank

print("Test 1 : DMA and accelerator reset values")
stest.expect_equal(bank.WPREF_CONTROL, 0x0)
stest.expect_equal(bank.WDISP_STATUS, 0x2)
stest.expect_equal(bank.FPGA_ID, 0x01010003)
stest.expect_equal(bank.ACCEL_CONTROL, 0x8000)

print("Test 2 : WPREF_CONTROL RUN bit")
regs.wpref_control.write(regs._wpref_control_layout.value(RUN=1))
stest.expect_equal(
    regs.wpref_control_fields(regs.wpref_control.read()),
    {"RUN": 1, "RESERVED": 0, "RESET": 0, "IRQ_EN": 0},
)

print("Test 3 : WPREF_STATUS write-1-to-clear")
bank.WPREF_STATUS = 0x1
stest.expect_equal(regs.wpref_status.read(), 0x1)
regs.wpref_status.write(0x1)
stest.expect_equal(regs.wpref_status.read(), 0x0)

print("Test 4 : dispatcher and FPGA ID frontdoor read")
stest.expect_equal(regs.wdisp_status.read(), 0x2)
stest.expect_equal(regs.fpga_id.read(), 0x01010003)

print("Test 5 : ACCEL_CONTROL held in reset")
stest.expect_equal(regs.accel_control.read(), 0x8000)

print("PASS: simics cca-accel csr_registers")
