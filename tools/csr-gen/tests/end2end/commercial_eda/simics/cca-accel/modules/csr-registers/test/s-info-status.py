import info_status
import simics
import stest
import csr_registers_common

info_status.check_for_info_status(["csr-registers"])

dev = csr_registers_common.create_csr_registers()

for obj in [dev]:
    for cmd in ["info", "status"]:
        try:
            simics.SIM_run_command(obj.name + "." + cmd)
        except simics.SimExc_General as error:
            stest.fail(cmd + " command failed: " + str(error))
