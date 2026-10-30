#!/usr/bin/env bash
# Shared Simics workspace logic for simics/<case>/test.sh (source, do not execute).
# Requires CASE_DIR (absolute path to the case directory).

set -euo pipefail

_simics_common_init() {
  REPO_ROOT=$(cd "${CASE_DIR}/../../../../.." && pwd)
  CASE_NAME=$(basename "${CASE_DIR}")
  INPUT_MD="${INPUT_MD:-${REPO_ROOT}/specs/golden/${CASE_NAME}/regs.md}"
  SECTION_FILE="${CASE_DIR}/section.txt"
  if [[ ! -f "${SECTION_FILE}" ]]; then
    SECTION_FILE="${REPO_ROOT}/specs/golden/${CASE_NAME}/section.txt"
  fi
  SECTION=$(tr -d '\n' <"${SECTION_FILE}")
  MODULE_DIR="${CASE_DIR}/modules/csr-registers"
  DML_FILE="${MODULE_DIR}/csr_registers.dml"
  CSR_GEN="${CSR_GEN:-csr-gen}"
  if ! command -v "${CSR_GEN}" >/dev/null 2>&1; then
    FALLBACK_CSR_GEN="${REPO_ROOT}/work/csr-gen/bin/csr-gen"
    if [[ -x "${FALLBACK_CSR_GEN}" ]]; then
      CSR_GEN="${FALLBACK_CSR_GEN}"
    fi
  fi
  SIMICS_CLI="${SIMICS_CLI:-simics_intelfpga_cli}"
}

run_simics_case() {
  _simics_common_init

  if ! command -v "${CSR_GEN}" >/dev/null 2>&1; then
    echo "error: ${CSR_GEN} not found on PATH" >&2
    exit 127
  fi
  if ! command -v "${SIMICS_CLI}" >/dev/null 2>&1; then
    echo "error: ${SIMICS_CLI} not found on PATH. Install Simics and put it on PATH." >&2
    # shellcheck source=../print_tool_hint.sh
    source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/print_tool_hint.sh"
    print_eda_tool_hint "${REPO_ROOT}"
    exit 127
  fi
  if [[ ! -f "${INPUT_MD}" ]]; then
    echo "error: markdown input not found at ${INPUT_MD}" >&2
    exit 1
  fi
  if [[ ! -f "${MODULE_DIR}/Makefile" ]]; then
    echo "error: checked-in module not found at ${MODULE_DIR}" >&2
    exit 1
  fi

  cd "${CASE_DIR}"
  if [[ ! -x "${CASE_DIR}/bin/test-runner" ]]; then
    echo "INFO: initialize Simics workspace in ${CASE_DIR}"
    "${SIMICS_CLI}" --reinitialize
  fi

  echo "INFO: generate csr_registers.dml from ${INPUT_MD}"
  "${CSR_GEN}" generate \
    --input-file "${INPUT_MD}" \
    --input-format markdown \
    --markdown-section "${SECTION}" \
    --output-file "${DML_FILE}" \
    --output-format dml

  echo "INFO: build Simics module csr-registers"
  make MODULE=csr-registers

  TEST_LOG="${CASE_DIR}/logs/test/linux64/modules/csr-registers/test/test.log"
  echo "INFO: run Simics tests with bin/test-runner -v"
  set +e
  ./bin/test-runner -v --suite=modules/csr-registers/test
  TEST_RESULT=$?
  set -e

  if [[ -f "${TEST_LOG}" ]]; then
    echo "INFO: ${TEST_LOG}"
    cat "${TEST_LOG}"
  else
    echo "warning: test log not found at ${TEST_LOG}" >&2
  fi

  if [[ ${TEST_RESULT} -ne 0 ]]; then
    echo "error: Simics test-runner failed (exit ${TEST_RESULT})" >&2
    exit "${TEST_RESULT}"
  fi

  echo "INFO: simics tests passed (${CASE_NAME})"
}
