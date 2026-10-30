import stest
import csr_registers_common

dev = csr_registers_common.create_csr_registers()
regs = csr_registers_common.Registers(dev)
bank = regs.bank

print("Test 1 : reset values")
stest.expect_equal(bank.CTRL, 0x2)
stest.expect_equal(regs.ctrl_fields(bank.CTRL), {"ENABLE": 0, "MODE": 1})
stest.expect_equal(bank.EVENTS, 0x0)

print("Test 2 : backdoor CTRL read/write")
bank.CTRL = 0x5
stest.expect_equal(bank.CTRL, 0x5)

print("Test 3 : frontdoor ENABLE and MODE")
regs.ctrl.write(regs._ctrl_layout.value(ENABLE=1, MODE=0x2))
stest.expect_equal(regs.ctrl_fields(regs.ctrl.read()), {"ENABLE": 1, "MODE": 2})

print("Test 4 : EVENTS pending write-1-to-clear")
bank.EVENTS = 0xAA
stest.expect_equal(regs.events.read(), 0xAA)
regs.events.write(0xFF)
stest.expect_equal(regs.events.read(), 0x0)

print("PASS: simics example-device csr_registers")
