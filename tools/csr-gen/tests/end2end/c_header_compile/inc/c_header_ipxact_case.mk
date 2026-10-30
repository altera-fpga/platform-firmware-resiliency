# IP-XACT -> C header, then compile / run (requires INPUT_XML and SECTION).
ifndef INPUT_XML
$(error INPUT_XML must be set by the case Makefile)
endif

ifndef SECTION
$(error SECTION must be set by the case Makefile)
endif

ifndef INC_DIR
$(error INC_DIR must be set by the case Makefile)
endif

BUILD_DIR ?= build
GENERATED_H := $(BUILD_DIR)/regs.h
TEST_BIN := $(BUILD_DIR)/test_program
CSR_GEN ?= csr-gen
MOCK_C := $(INC_DIR)/reg_access_mock.c
TEST_COMMON_C := $(INC_DIR)/c_header_test.c

include $(INC_DIR)/c_header_test_flags.mk

# Phony header: regenerate on every test run when the reader or writer changes.
.PHONY: test clean generate generate-h compile run format $(GENERATED_H)
test: generate compile run

$(BUILD_DIR):
>mkdir -p $@

generate: generate-h

generate-h: $(GENERATED_H)

$(GENERATED_H): $(INPUT_XML) | $(BUILD_DIR)
ifdef IPXACT_ADDRESS_BLOCK
>$(CSR_GEN) generate \
>	--input-file $(INPUT_XML) \
>	--input-format ip-xact \
>	--ipxact-address-block $(IPXACT_ADDRESS_BLOCK) \
>	--markdown-section "$(SECTION)" \
>	--output-file $@ \
>	--output-format c-header
else
>$(CSR_GEN) generate \
>	--input-file $(INPUT_XML) \
>	--input-format ip-xact \
>	--markdown-section "$(SECTION)" \
>	--output-file $@ \
>	--output-format c-header
endif

compile: $(TEST_BIN)

$(TEST_BIN): test.c $(GENERATED_H) $(MOCK_C) $(TEST_COMMON_C) | $(BUILD_DIR)
>$(CC) $(CFLAGS) -I$(BUILD_DIR) -I$(INC_DIR) test.c $(MOCK_C) $(TEST_COMMON_C) -o $@

run: $(TEST_BIN)
>$(TEST_BIN)

clean:
>rm -rf $(BUILD_DIR)

format:
>$(MAKE) -C $(REPO_ROOT) style-format-clang
