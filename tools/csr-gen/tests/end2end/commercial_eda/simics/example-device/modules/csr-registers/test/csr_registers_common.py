import dev_util
import simics


def create_csr_registers(name=None):
    """Create a csr_registers Simics device."""
    new_dev = simics.pre_conf_object(name, "csr_registers")
    simics.SIM_add_configuration([new_dev], None)
    return simics.SIM_get_object(new_dev.name)


class Registers:
    """Frontdoor register helpers for the example-device CSR map."""

    def __init__(self, dut):
        bank = dut.bank.csr_registers
        self._ctrl_layout = dev_util.Bitfield_LE(
            {
                "ENABLE": 0,
                "MODE": (2, 1),
            }
        )
        self._events_layout = dev_util.Bitfield_LE({"PENDING": (7, 0)})
        self.ctrl = dev_util.Register_LE(bank, 0x00, 4, bitfield=self._ctrl_layout)
        self.events = dev_util.Register_LE(bank, 0x04, 4, bitfield=self._events_layout)
        self.bank = bank

    def ctrl_fields(self, value):
        return self._ctrl_layout.fields(value)
