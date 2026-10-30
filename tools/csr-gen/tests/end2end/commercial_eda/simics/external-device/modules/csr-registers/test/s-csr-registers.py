import stest
import csr_registers_common

dev = csr_registers_common.create_csr_registers()
regs = csr_registers_common.Registers(dev)
bank = regs.bank

print("Test 1 : reset values")
stest.expect_equal(bank.STATUS, 0x0)
stest.expect_equal(bank.FIFO, 0x0)
stest.expect_equal(bank.MEM[0], 0x0)

print("Test 2 : STATUS read-only flag")
bank.STATUS = 0x1
stest.expect_equal(bank.STATUS, 0x1)
stest.expect_equal(regs.status.read(), 0x1)

print("Test 3 : FIFO payload and fill level")
bank.FIFO = (0x10 << 8) | 0x42
stest.expect_equal(regs.fifo_fields(regs.fifo.read()), {"DATA": 0x42, "LEVEL": 0x10})
current = regs.fifo.read()
regs.fifo.write(regs._fifo_layout.value(current, DATA=0x55))
stest.expect_equal(regs.fifo_fields(regs.fifo.read()), {"DATA": 0x55, "LEVEL": 0x10})

print("Test 4 : MEM read/write window")
bank.MEM[1] = 0xAABBCCDD
stest.expect_equal(bank.MEM[1], 0xAABBCCDD)
regs.mem.write(0x01020304)
stest.expect_equal(regs.mem.read(), 0x01020304)

print("Test 5 : ROM read-only and WBUF write-only arrays")
bank.ROM[0] = 0xDEADBEEF
stest.expect_equal(regs.rom.read(), 0xDEADBEEF)
regs.wbuf.write(0x55556666)
stest.expect_equal(bank.WBUF[0], 0x55556666)

print("PASS: simics external-device csr_registers")
