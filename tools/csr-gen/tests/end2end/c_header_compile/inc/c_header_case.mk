# Shared generate / compile / run rules for c_header_compile cases.
# Set REPO_ROOT, INPUT_MD, and SECTION before including this file.

ifndef INPUT_MD
$(error INPUT_MD must be set by the case Makefile)
endif

ifndef SECTION
$(error SECTION must be set by the case Makefile)
endif

BUILD_DIR ?= build
GENERATED_H := $(BUILD_DIR)/regs.h
TEST_BIN := $(BUILD_DIR)/test_program
CSR_GEN ?= csr-gen
INC_DIR ?= ../inc
MOCK_C := $(INC_DIR)/reg_access_mock.c
TEST_COMMON_C := $(INC_DIR)/c_header_test.c

include $(INC_DIR)/c_header_test_flags.mk

# Phony header: regenerate on every test run when the writer changes.
.PHONY: test clean generate compile run format $(GENERATED_H)
test: generate compile run

$(BUILD_DIR):
>mkdir -p $@

generate: $(GENERATED_H)

$(GENERATED_H): $(INPUT_MD) | $(BUILD_DIR)
>$(CSR_GEN) generate \
>	--input-file $(INPUT_MD) \
>	--input-format markdown \
>	--markdown-section "$(SECTION)" \
>	--output-file $@ \
>	--output-format c-header

compile: $(TEST_BIN)

$(TEST_BIN): test.c $(GENERATED_H) $(MOCK_C) $(TEST_COMMON_C) | $(BUILD_DIR)
>$(CC) $(CFLAGS) -I$(BUILD_DIR) -I$(INC_DIR) test.c $(MOCK_C) $(TEST_COMMON_C) -o $@

run: $(TEST_BIN)
>$(TEST_BIN)

clean:
>rm -rf $(BUILD_DIR)

format:
>$(MAKE) -C $(REPO_ROOT) style-format-clang
