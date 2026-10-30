import dev_util
import simics

WPREF_CONTROL_ADDR = 0x30204000
WPREF_STATUS_ADDR = 0x30204010
WDISP_STATUS_ADDR = 0x30204040
FPGA_ID_ADDR = 0x30400000
ACCEL_CONTROL_ADDR = 0x30400010


def create_csr_registers(name=None):
    """Create a csr_registers Simics device for the cca_accel map."""
    new_dev = simics.pre_conf_object(name, "csr_registers")
    simics.SIM_add_configuration([new_dev], None)
    return simics.SIM_get_object(new_dev.name)


class Registers:
    """Frontdoor helpers for representative cca_accel CSR registers."""

    def __init__(self, dut):
        bank = dut.bank.csr_registers
        self._wpref_control_layout = dev_util.Bitfield_LE(
            {
                "IRQ_EN": 3,
                "RESET": 2,
                "RESERVED": 1,
                "RUN": 0,
            }
        )
        self.wpref_control = dev_util.Register_LE(
            bank, WPREF_CONTROL_ADDR, 4, bitfield=self._wpref_control_layout
        )
        self.wpref_status = dev_util.Register_LE(bank, WPREF_STATUS_ADDR, 4)
        self.wdisp_status = dev_util.Register_LE(bank, WDISP_STATUS_ADDR, 4)
        self.fpga_id = dev_util.Register_LE(bank, FPGA_ID_ADDR, 4)
        self.accel_control = dev_util.Register_LE(bank, ACCEL_CONTROL_ADDR, 4)
        self.bank = bank

    def wpref_control_fields(self, value):
        return self._wpref_control_layout.fields(value)
