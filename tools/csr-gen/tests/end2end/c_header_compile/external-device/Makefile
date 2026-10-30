# external-device: generate C header from golden regs.md, compile test.c, run.
SHELL := /bin/bash -o pipefail
.RECIPEPREFIX := >

REPO_ROOT := $(abspath ../../../..)
INPUT_MD := $(REPO_ROOT)/specs/golden/external-device/regs.md
SECTION := $(shell cat $(REPO_ROOT)/specs/golden/external-device/section.txt | tr -d '\n')

include ../inc/c_header_case.mk
