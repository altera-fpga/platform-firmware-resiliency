# CSV -> Markdown -> C header, then compile / run (requires INPUT_CSV and SECTION).
ifndef INPUT_CSV
$(error INPUT_CSV must be set by the case Makefile)
endif

ifndef SECTION
$(error SECTION must be set by the case Makefile)
endif

BUILD_DIR ?= build
CSV_STEM := $(basename $(notdir $(INPUT_CSV)))
GENERATED_MD := $(BUILD_DIR)/$(CSV_STEM).md
GENERATED_H := $(BUILD_DIR)/regs.h
TEST_BIN := $(BUILD_DIR)/test_program
CSR_GEN ?= csr-gen
INC_DIR ?= ../inc
MOCK_C := $(INC_DIR)/reg_access_mock.c
TEST_COMMON_C := $(INC_DIR)/c_header_test.c

include $(INC_DIR)/c_header_test_flags.mk

# Phony outputs: regenerate Markdown and the header on every test run.
.PHONY: test clean generate generate-md generate-h compile run format $(GENERATED_MD) $(GENERATED_H)
test: generate compile run

$(BUILD_DIR):
>mkdir -p $@

generate: generate-h

generate-h: $(GENERATED_H)

generate-md: $(GENERATED_MD)

$(GENERATED_MD): $(INPUT_CSV) | $(BUILD_DIR)
>$(CSR_GEN) generate \
>	--input-file $(INPUT_CSV) \
>	--input-format csv \
>	--output-file $@ \
>	--output-format markdown

$(GENERATED_H): $(GENERATED_MD)
>$(CSR_GEN) generate \
>	--input-file $(GENERATED_MD) \
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
