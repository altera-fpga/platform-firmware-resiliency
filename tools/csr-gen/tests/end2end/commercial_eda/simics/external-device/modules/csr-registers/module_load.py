# SPDX-License-Identifier: MIT-0

import cli

class_name = "csr_registers"

#
# ------------------------ info -----------------------
#


def get_info(obj):
    # TODO: Return something useful here
    return []


cli.new_info_command(class_name, get_info)

#
# ------------------------ status -----------------------
#


def get_status(obj):
    bank = obj.bank.csr_registers
    flag = bank.STATUS & 1
    return [("Registers", [("FLAG", flag)])]


cli.new_status_command(class_name, get_status)
