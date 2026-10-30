
THIS_MK_ABSPATH := $(abspath $(lastword $(MAKEFILE_LIST)))
THIS_MK_DIR := $(dir $(THIS_MK_ABSPATH))

# Enable pipefail for all commands
SHELL=/bin/bash -o pipefail

# Enable second expansion
.SECONDEXPANSION:

# Clear all built in suffixes
.SUFFIXES:

NOOP :=
SPACE := $(NOOP) $(NOOP)
COMMA := ,
HOSTNAME := $(shell hostname)

##############################################################################
# Environment check
##############################################################################


##############################################################################
# Configuration
##############################################################################
WORK_ROOT := $(abspath $(THIS_MK_DIR)/work)
PROJECT_DIR_ABS := $(abspath $(THIS_MK_DIR))

# Installed package layout: $(INSTALL_ROOT)/csr-gen/{venv,bin}.
INSTALL_ROOT ?= $(WORK_ROOT)
INSTALL_GUI ?= 1
INSTALL_DIR := $(INSTALL_ROOT)/csr-gen
INSTALL_VENV_DIR := $(INSTALL_DIR)/venv
INSTALL_BIN_DIR := $(INSTALL_DIR)/bin
INSTALL_VENV_DONE := $(INSTALL_DIR)/.done
INSTALL_VENV_PYTHON := $(INSTALL_VENV_DIR)/bin/python
INSTALL_VENV_PIP := $(INSTALL_VENV_DIR)/bin/pip
INSTALL_VENV_PIP_INSTALL := $(INSTALL_VENV_PIP) install $(PIP_PROXY) --no-cache-dir --timeout 120 --retries 20 --trusted-host pypi.org --trusted-host files.pythonhosted.org
WRITE_INSTALL_WRAPPER := $(THIS_MK_DIR)scripts/write_install_wrapper.sh

# Parallel pytest (pytest-xdist) for end-to-end tests. Set PYTEST_XDIST=0 to disable.
PYTEST_XDIST ?= 1
PYTEST_WORKERS ?= auto
ifeq ($(filter 0 false no,$(PYTEST_XDIST)),)
PYTEST_PARALLEL := -n $(PYTEST_WORKERS)
else
PYTEST_PARALLEL :=
endif


PYTHON3 ?= python3
VENV_DIR := venv
VENV_DONE := $(VENV_DIR)/.done
VENV_PY := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip
ifneq ($(https_proxy),)
PIP_PROXY := --proxy $(https_proxy)
else
PIP_PROXY :=
endif
VENV_PIP_INSTALL := $(VENV_PIP) install $(PIP_PROXY) --no-cache-dir --timeout 120 --retries 20 --trusted-host pypi.org --trusted-host files.pythonhosted.org
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_CLANG_FORMAT := $(VENV_DIR)/bin/clang-format
BLACK := $(VENV_DIR)/bin/black --workers 1

# Installed-package wrappers on PATH for end-to-end tests and scripts that invoke csr-gen.
export PATH := $(INSTALL_BIN_DIR):$(PATH)

VERIBLE_FORMATER ?= verible-verilog-format

REQUIRED_TEST_COVERAGE := 95

##############################################################################
# Set default goal before any targets. The default goal here is "test"
##############################################################################
DEFAULT_TARGET := all

.DEFAULT_GOAL := default
.PHONY: default
default: $(DEFAULT_TARGET)


##############################################################################
# Makefile starts here
##############################################################################


###############################################################################
#                          UTILITY TARGETS
###############################################################################
# Prep workspace
$(VENV_DONE): requirements.txt pyproject.toml
	$(PYTHON3) -m venv --clear $(VENV_DIR)
	$(VENV_PIP_INSTALL) --upgrade pip
	$(VENV_PIP_INSTALL) -r requirements.txt
	$(VENV_PIP_INSTALL) -e .
	touch $@

.PHONY: venv
venv: $(VENV_DONE)

.PHONY: venv-freeze
venv-freeze:
	$(VENV_PIP) freeze > requirements.txt
	sed -i -e 's/==/~=/g' requirements.txt

.PHONY: prepare-tools
prepare-tools : venv

$(WORK_ROOT):
	mkdir -p $(WORK_ROOT)

# Deep clean using git
.PHONY: dev-clean
dev-clean :
	git clean -dfx --exclude=/.vscode --exclude=/*.code-workspace

.PHONY: clean
clean:
	rm -rf $(WORK_ROOT)

.PHONY: prep
prep:

# `build` stays the entry point. Install depends on the stamp, not the phony
# target, so a later `make install` reuses work/csr-gen when sources are unchanged.
BUILD_STAMP := $(WORK_ROOT)/.build-stamp
BUILD_SOURCES := $(THIS_MK_DIR)pyproject.toml $(THIS_MK_DIR)README.md \
	$(shell find $(THIS_MK_DIR)src -type f -name '*.py' ! -path '*/__pycache__/*' | sort)

$(BUILD_STAMP): $(BUILD_SOURCES) | $(WORK_ROOT) venv
	$(VENV_PYTHON) -m build
	touch $@

.PHONY: build
build: $(BUILD_STAMP)

PKG_VERSION := $(shell sed -n 's/^version = "\(.*\)"/\1/p' $(THIS_MK_DIR)pyproject.toml)
RELEASE_DROP := $(abspath $(THIS_MK_DIR)/../..)/install

.PHONY: release-assets
release-assets: $(BUILD_STAMP)
	mkdir -p $(RELEASE_DROP)
	rm -f $(RELEASE_DROP)/csr_gen-*.whl $(RELEASE_DROP)/csr_gen-*.tar.gz $(RELEASE_DROP)/csr-markdown.zip
	cp dist/csr_gen-$(PKG_VERSION)-py3-none-any.whl dist/csr_gen-$(PKG_VERSION).tar.gz $(RELEASE_DROP)/
	cd $(THIS_MK_DIR)docs/skills && zip -r $(RELEASE_DROP)/csr-markdown.zip csr-markdown

$(INSTALL_VENV_DONE): requirements.txt $(BUILD_STAMP)
	mkdir -p $(INSTALL_DIR)
	$(PYTHON3) -m venv --clear $(INSTALL_VENV_DIR)
	$(INSTALL_VENV_PIP_INSTALL) --upgrade pip
	$(INSTALL_VENV_PIP_INSTALL) -r requirements.txt
ifeq ($(filter 0 false no,$(INSTALL_GUI)),)
	set -e; wheel=$$(ls -1 dist/*.whl | head -1); \
	$(INSTALL_VENV_PIP_INSTALL) --force-reinstall "$${wheel}[gui]"
else
	$(INSTALL_VENV_PIP_INSTALL) --force-reinstall dist/*.whl
endif
	mkdir -p $(INSTALL_BIN_DIR)
	$(WRITE_INSTALL_WRAPPER) $(INSTALL_BIN_DIR)/csr-gen csr-gen
ifeq ($(filter 0 false no,$(INSTALL_GUI)),)
	$(WRITE_INSTALL_WRAPPER) $(INSTALL_BIN_DIR)/csr-gen-gui csr-gen-gui
else
	rm -f $(INSTALL_BIN_DIR)/csr-gen-gui
endif
	touch $@

.PHONY: install
install: $(INSTALL_VENV_DONE)

.PHONY: install-gui
install-gui: install

EDA_VENV_DIR := $(WORK_ROOT)/eda-venv
EDA_VENV_DONE := $(EDA_VENV_DIR)/.done
EDA_VENV_PYTHON := $(EDA_VENV_DIR)/bin/python
EDA_VENV_PIP := $(EDA_VENV_DIR)/bin/pip
EDA_VENV_PIP_INSTALL := $(EDA_VENV_PIP) install $(PIP_PROXY) --no-cache-dir --timeout 120 --retries 20 --trusted-host pypi.org --trusted-host files.pythonhosted.org

$(EDA_VENV_DONE): requirements.txt requirements-eda.txt $(BUILD_STAMP) | $(WORK_ROOT)
	$(PYTHON3) -m venv --clear $(EDA_VENV_DIR)
	$(EDA_VENV_PIP_INSTALL) --upgrade pip
	$(EDA_VENV_PIP_INSTALL) -r requirements.txt
	$(EDA_VENV_PIP_INSTALL) -r requirements-eda.txt
	$(EDA_VENV_PIP_INSTALL) --force-reinstall dist/*.whl
	touch $@

# Full-suite venv: dev/test deps, PeakRDL, GUI extra, and installed csr-gen wheel.
TEST_ALL_VENV_DIR := $(WORK_ROOT)/test-all-venv
TEST_ALL_VENV_DONE := $(TEST_ALL_VENV_DIR)/.done
TEST_ALL_VENV_PYTHON := $(TEST_ALL_VENV_DIR)/bin/python
TEST_ALL_VENV_PIP := $(TEST_ALL_VENV_DIR)/bin/pip
TEST_ALL_VENV_PIP_INSTALL := $(TEST_ALL_VENV_PIP) install $(PIP_PROXY) --no-cache-dir --timeout 120 --retries 20 --trusted-host pypi.org --trusted-host files.pythonhosted.org

$(TEST_ALL_VENV_DONE): requirements.txt requirements-eda.txt $(BUILD_STAMP) | $(WORK_ROOT)
	$(PYTHON3) -m venv --clear $(TEST_ALL_VENV_DIR)
	$(TEST_ALL_VENV_PIP_INSTALL) --upgrade pip
	$(TEST_ALL_VENV_PIP_INSTALL) -r requirements.txt
	$(TEST_ALL_VENV_PIP_INSTALL) -r requirements-eda.txt
	$(TEST_ALL_VENV_PIP_INSTALL) --force-reinstall --no-deps dist/*.whl
	$(TEST_ALL_VENV_PIP_INSTALL) 'PySide6>=6.6,<7'
	touch $@

.PHONY: test-all-venv
test-all-venv: $(TEST_ALL_VENV_DONE)

.PHONY: test
test: test-unittests test-smoketest test-c-header-compile

.PHONY: test-unittests
test-unittests: | venv
	$(VENV_PYTHON) -m pytest --cov=csr_gen --cov-report=term-missing --cov-fail-under=$(REQUIRED_TEST_COVERAGE) tests/unittests

.PHONY: test-gui
test-gui: | venv
	$(VENV_PYTHON) -m pytest --cov=csr_gen_gui --cov-report=term-missing tests/gui --ignore=tests/gui/test_main_window_smoke.py

.PHONY: test-gui-smoke
test-gui-smoke: | venv
	$(VENV_PIP_INSTALL) -e ".[gui]"
	QT_QPA_PLATFORM=offscreen $(VENV_PYTHON) -m pytest tests/gui/test_main_window_smoke.py

.PHONY: test-smoketest
test-smoketest: install
	$(INSTALL_VENV_PYTHON) -m pytest $(PYTEST_PARALLEL) tests/end2end/smoketest

.PHONY: test-c-header-compile
test-c-header-compile: install
	$(INSTALL_VENV_PYTHON) -m pytest $(PYTEST_PARALLEL) tests/end2end/c_header_compile

.PHONY: test-end2end-eda
test-end2end-eda: $(EDA_VENV_DONE)
	$(EDA_VENV_PYTHON) -m pytest $(PYTEST_PARALLEL) tests/end2end/eda

.PHONY: test-end2end-commercial-eda
test-end2end-commercial-eda: install
	$(INSTALL_VENV_PYTHON) -m pytest $(PYTEST_PARALLEL) tests/end2end/commercial_eda

.PHONY: test-end2end-commercial-quartus-sv-compile
test-end2end-commercial-quartus-sv-compile: install
	$(INSTALL_VENV_PYTHON) -m pytest $(PYTEST_PARALLEL) tests/end2end/commercial_eda/quartus_sv_compile

.PHONY: test-end2end-commercial-vcs-sim
test-end2end-commercial-vcs-sim: install
	$(INSTALL_VENV_PYTHON) -m pytest $(PYTEST_PARALLEL) tests/end2end/commercial_eda/vcs_sim

.PHONY: test-end2end-commercial-simics
test-end2end-commercial-simics: install
	$(INSTALL_VENV_PYTHON) -m pytest $(PYTEST_PARALLEL) tests/end2end/commercial_eda/simics

.PHONY: test-all
test-all: install $(TEST_ALL_VENV_DONE)
	PATH=$(INSTALL_BIN_DIR):$(TEST_ALL_VENV_DIR)/bin:$(PATH) QT_QPA_PLATFORM=offscreen $(TEST_ALL_VENV_PYTHON) -m pytest $(PYTEST_PARALLEL) --cov=csr_gen --cov-report=term-missing --cov-fail-under=$(REQUIRED_TEST_COVERAGE) tests

.PHONY: coverage-html
coverage-html: | venv
	$(VENV_PYTHON) -m pytest --cov=csr_gen --cov-report=html tests

.PHONY: doc-examples
doc-examples: | venv
	$(VENV_PYTHON) scripts/generate_examples_doc.py

.PHONY: doc-examples-check
doc-examples-check: | venv
	$(VENV_PYTHON) scripts/generate_examples_doc.py --check

# Recursive so an included makefile can append commands before the recipe runs.
GEN_TEST_OUTPUT_CMDS = \
	$(VENV_PYTHON) -m csr_gen generate --input-file specs/golden/example-device/regs.md --input-format markdown --markdown-section "CSR Registers" --output-file $(WORK_ROOT)/regs.sv --output-format systemverilog --output-file $(WORK_ROOT)/regs.h --output-format c-header --output-file $(WORK_ROOT)/regs.xml --output-format ip-xact --output-file $(WORK_ROOT)/regs.rdl --output-format systemrdl ; \
	$(VENV_PYTHON) -m csr_gen generate --input-file specs/golden/external-device/regs.md --input-format markdown --markdown-section "CSR Registers" --output-file $(WORK_ROOT)/ext_regs.sv --output-format systemverilog --output-file $(WORK_ROOT)/ext_regs.h --output-format c-header --output-file $(WORK_ROOT)/ext_regs.xml --output-format ip-xact --output-file $(WORK_ROOT)/ext_regs.rdl --output-format systemrdl ; \
	$(VENV_PYTHON) -m csr_gen generate --input-file tests/testdata/pqc_ip.csv --input-format csv --output-file $(WORK_ROOT)/pqc_ip.sv --output-format systemverilog --output-file $(WORK_ROOT)/pqc_ip.h --output-format c-header --output-file $(WORK_ROOT)/pqc_ip.rdl --output-format systemrdl

.PHONY: gen-test-output
gen-test-output: | venv $(WORK_ROOT)
	$(GEN_TEST_OUTPUT_CMDS)

.PHONY: sim
sim:

.PHONY: all
all: build test

-include tests/private-tests/Makefile

ifneq ($(wildcard tests/private-tests/Makefile),)
dev-clean: test-priv-dev-clean
endif

###############################################################################
#                          Style Checks
###############################################################################

STYLE_FORMAT_VERILOG_FILES := $(shell git ls-files \
	**/*.v \
	**/*.sv \
)

.PHONY: style-format-verilog
style-format-verilog:
	$(VERIBLE_FORMATER) --flagfile verible-format.txt --inplace --verbose $(STYLE_FORMAT_VERILOG_FILES)

.PHONY: style-check-verilog
style-check-verilog:
	$(VERIBLE_FORMATER) --flagfile verible-format.txt --inplace --verify --verbose $(STYLE_FORMAT_VERILOG_FILES)


CPP_STYLE_CHECK_FILES := $(shell find tests -type f \( -name '*.c' -o -name '*.h' \) ! -path '*/build/*' 2>/dev/null | sort)

.PHONY: style-check-clang
style-check-clang: | venv
	$(VENV_CLANG_FORMAT) --style=file -n -i $(CPP_STYLE_CHECK_FILES)

.PHONY: style-format-clang
style-format-clang: | venv
	$(VENV_CLANG_FORMAT) --style=file -i $(CPP_STYLE_CHECK_FILES)

.PHONY: style-format-black
style-format-black: | venv
	$(VENV_DIR)/bin/black --version
	$(BLACK) .

.PHONY: style-check-black
style-check-black: | venv
	$(VENV_DIR)/bin/black --version
	$(BLACK) . --check --diff

.PHONY: style-check-flake8
style-check-flake8: | venv
	$(VENV_DIR)/bin/flake8 --version
	$(VENV_DIR)/bin/flake8

.PHONY: style-check
style-check: style-check-black style-check-flake8

.PHONY: style-format
style-format: style-format-black


###############################################################################
#                                HELP
###############################################################################
.PHONY: help
help:
	$(info CSR-Gen Build)
	$(info    Project Directory : $(PROJECT_DIR_ABS))
