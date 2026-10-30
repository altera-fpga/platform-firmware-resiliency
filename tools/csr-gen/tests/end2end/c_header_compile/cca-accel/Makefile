# cca-accel: C header compile test for cca_accel.md (CSR Registers).
SHELL := /bin/bash -o pipefail
.RECIPEPREFIX := >

REPO_ROOT := $(abspath ../../../..)
INPUT_MD := $(REPO_ROOT)/tests/testdata/cca_accel.md
SECTION := $(shell cat section.txt | tr -d '\n')

include ../inc/c_header_case.mk
