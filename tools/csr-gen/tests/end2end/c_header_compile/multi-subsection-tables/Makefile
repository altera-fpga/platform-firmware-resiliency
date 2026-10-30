# multi-subsection-tables: Markdown with tables in section body and subsection.
SHELL := /bin/bash -o pipefail
.RECIPEPREFIX := >

REPO_ROOT := $(abspath ../../../..)
INPUT_MD := $(REPO_ROOT)/tests/testdata/multi_subsection_tables.md
SECTION := $(shell cat section.txt | tr -d '\n')

include ../inc/c_header_case.mk
