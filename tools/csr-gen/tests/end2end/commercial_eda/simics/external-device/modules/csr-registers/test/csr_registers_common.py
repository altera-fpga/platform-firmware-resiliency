import dev_util
import simics


def create_csr_registers(name=None):
    """Create a csr_registers Simics device."""
    new_dev = simics.pre_conf_object(name, "csr_registers")
    simics.SIM_add_configuration([new_dev], None)
    return simics.SIM_get_object(new_dev.name)


class Registers:
    """Frontdoor register helpers for the external-device CSR map."""

    def __init__(self, dut):
        bank = dut.bank.csr_registers
        self._status_layout = dev_util.Bitfield_LE({"FLAG": 0})
        self._fifo_layout = dev_util.Bitfield_LE(
            {
                "DATA": (7, 0),
                "LEVEL": (15, 8),
            }
        )
        self.status = dev_util.Register_LE(bank, 0x00, 4, bitfield=self._status_layout)
        self.fifo = dev_util.Register_LE(bank, 0x10, 4, bitfield=self._fifo_layout)
        self.mem = dev_util.Register_LE(bank, 0x20, 4)
        self.rom = dev_util.Register_LE(bank, 0x30, 4)
        self.wbuf = dev_util.Register_LE(bank, 0x40, 4)
        self.bank = bank

    def fifo_fields(self, value):
        return self._fifo_layout.fields(value)
