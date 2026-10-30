MODULE_CLASSES = csr_registers
SRC_FILES = csr_registers.dml
PYTHON_FILES = module_load.py

SIMICS_API := latest
THREAD_SAFE := yes

ifeq ($(MODULE_MAKEFILE),)
$(error Make sure you compile your module from the project directory)
else
include $(MODULE_MAKEFILE)
endif
