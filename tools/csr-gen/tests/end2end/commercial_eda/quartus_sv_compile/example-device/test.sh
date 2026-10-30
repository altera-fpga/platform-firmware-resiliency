#!/usr/bin/env bash
# Synthesize example-device CSR RTL with Quartus (manual or CI via pytest).
set -euo pipefail

CASE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${CASE_DIR}/../../../../.." && pwd)
COMPILE_ROOT=$(cd "${CASE_DIR}/.." && pwd)
CASE_NAME=$(basename "${CASE_DIR}")
INPUT_MD="${REPO_ROOT}/specs/golden/${CASE_NAME}/regs.md"
SECTION_FILE="${CASE_DIR}/section.txt"
if [[ ! -f "${SECTION_FILE}" ]]; then
  SECTION_FILE="${REPO_ROOT}/specs/golden/${CASE_NAME}/section.txt"
fi
SECTION=$(tr -d '\n' <"${SECTION_FILE}")
CSR_GEN="${CSR_GEN:-csr-gen}"
SYN_REPORT="${CASE_DIR}/output_files/test.syn.rpt"
IGNORE_FILE="${CASE_DIR}/ignored_syn_messages.txt"

if ! command -v "${CSR_GEN}" >/dev/null 2>&1; then
  echo "error: ${CSR_GEN} not found on PATH" >&2
  exit 127
fi
if ! command -v quartus_syn >/dev/null 2>&1; then
  echo "error: quartus_syn not found on PATH. Install Quartus and put it on PATH." >&2
  # shellcheck source=../../print_tool_hint.sh
  source "${CASE_DIR}/../../print_tool_hint.sh"
  print_eda_tool_hint "${REPO_ROOT}"
  exit 127
fi

echo "INFO: generate csr_registers.sv from ${INPUT_MD}"
"${CSR_GEN}" generate \
  --input-file "${INPUT_MD}" \
  --input-format markdown \
  --markdown-section "${SECTION}" \
  --output-file "${CASE_DIR}/csr_registers.sv" \
  --output-format systemverilog

echo "INFO: remove prior Quartus outputs"
rm -rf "${CASE_DIR}/output_files" "${CASE_DIR}/qdb" "${CASE_DIR}/dni"

echo "INFO: quartus_syn test -c test"
cd "${CASE_DIR}"
quartus_syn test -c test

echo "INFO: check ${SYN_REPORT}"
CHECK_ARGS=("${SYN_REPORT}")
if [[ -f "${IGNORE_FILE}" ]]; then
  CHECK_ARGS+=("${IGNORE_FILE}")
fi
if ! "${PYTHON:-python3}" "${COMPILE_ROOT}/syn_report_check.py" "${CHECK_ARGS[@]}"; then
  echo "error: synthesis report check failed; see ${SYN_REPORT} sections 12-14" >&2
  exit 1
fi

echo "INFO: quartus synthesis passed (zero effective warnings and errors)"
