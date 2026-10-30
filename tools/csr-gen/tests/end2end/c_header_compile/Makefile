# c_header_compile: run all per-case end-to-end C header compile tests.
SHELL := /bin/bash -o pipefail
.RECIPEPREFIX := >

REPO_ROOT := $(abspath ../../..)
CASES := example-device external-device multi-subsection-tables optional-no-reset-column pqc-ip cca-accel

.PHONY: test clean format $(CASES)

test: $(CASES)

$(CASES):
>$(MAKE) -C $@ test

clean:
>for case in $(CASES); do $(MAKE) -C $$case clean; done

format:
>$(MAKE) -C $(REPO_ROOT) style-format-clang
