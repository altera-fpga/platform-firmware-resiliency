# pqc-ip: CSV -> Markdown -> C header, then compile test.c and run.
SHELL := /bin/bash -o pipefail
.RECIPEPREFIX := >

REPO_ROOT := $(abspath ../../../..)
INPUT_CSV := $(REPO_ROOT)/tests/testdata/pqc_ip.csv
SECTION := $(shell cat section.txt | tr -d '\n')

include ../inc/c_header_csv_case.mk
