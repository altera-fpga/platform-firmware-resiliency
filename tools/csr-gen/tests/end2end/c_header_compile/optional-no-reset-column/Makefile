# optional-no-reset-column: Markdown table without a Reset column.
SHELL := /bin/bash -o pipefail
.RECIPEPREFIX := >

REPO_ROOT := $(abspath ../../../..)
INPUT_MD := $(REPO_ROOT)/tests/testdata/optional_no_reset_column.md
SECTION := $(shell cat section.txt | tr -d '\n')

include ../inc/c_header_case.mk
