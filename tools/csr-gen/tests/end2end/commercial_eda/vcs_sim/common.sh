#!/usr/bin/env bash
# Shared VCS compile/run logic for vcs_sim/<case>/test.sh (source, do not execute).
# Requires CASE_DIR (absolute path to the case directory).

set -euo pipefail

_vcs_sim_common_init() {
  REPO_ROOT=$(cd "${CASE_DIR}/../../../../.." && pwd)
  CASE_NAME=$(basename "${CASE_DIR}")
  INPUT_MD="${INPUT_MD:-${REPO_ROOT}/specs/golden/${CASE_NAME}/regs.md}"
  HARNESS_SV="${REPO_ROOT}/tests/end2end/commercial_eda/quartus_sv_compile/${CASE_NAME}/csr_synth_harness.sv"
  SECTION_FILE="${CASE_DIR}/section.txt"
  if [[ ! -f "${SECTION_FILE}" ]]; then
    SECTION_FILE="${REPO_ROOT}/specs/golden/${CASE_NAME}/section.txt"
  fi
  SECTION=$(tr -d '\n' <"${SECTION_FILE}")
  CSR_GEN="${CSR_GEN:-csr-gen}"
  if ! command -v "${CSR_GEN}" >/dev/null 2>&1; then
    FALLBACK_CSR_GEN="${REPO_ROOT}/work/csr-gen/bin/csr-gen"
    if [[ -x "${FALLBACK_CSR_GEN}" ]]; then
      CSR_GEN="${FALLBACK_CSR_GEN}"
    fi
  fi
  SIMV="${CASE_DIR}/simv"
  SIM_LOG="${CASE_DIR}/sim.log"
  PASS_MARKER="${PASS_MARKER:-PASS: vcs_sim ${CASE_NAME}}"
}

run_vcs_sim() {
  _vcs_sim_common_init

  if ! command -v "${CSR_GEN}" >/dev/null 2>&1; then
    echo "error: ${CSR_GEN} not found on PATH" >&2
    exit 127
  fi
  if ! command -v vcs >/dev/null 2>&1; then
    echo "error: vcs not found on PATH. Install vcs and put it on PATH." >&2
    # shellcheck source=../print_tool_hint.sh
    source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/print_tool_hint.sh"
    print_eda_tool_hint "${REPO_ROOT}"
    exit 127
  fi

  if [[ -z "${QUARTUS_SIM_LIB:-}" ]]; then
    if [[ -n "${QUARTUS_ROOTDIR:-}" && -f "${QUARTUS_ROOTDIR}/eda/sim_lib/altera_lnsim.sv" ]]; then
      QUARTUS_SIM_LIB="${QUARTUS_ROOTDIR}/eda/sim_lib"
    elif command -v quartus_sh >/dev/null 2>&1; then
      QUARTUS_SIM_LIB=$(quartus_sh --sim_lib_dir 2>/dev/null || true)
    fi
  fi
  if [[ -z "${QUARTUS_SIM_LIB:-}" || ! -f "${QUARTUS_SIM_LIB}/altera_lnsim.sv" ]]; then
    echo "error: set QUARTUS_SIM_LIB to Quartus eda/sim_lib (altera_lnsim.sv not found)" >&2
    exit 127
  fi

  ALTERA_LNSIM_SRC="${QUARTUS_SIM_LIB}/altera_lnsim.sv"
  WORK_LNSIM="${CASE_DIR}/work/altera_lnsim.sv"
  LNSIM_PATCH_ID="${CASE_DIR}/work/.altera_lnsim_vcs_patch_id"
  LNSIM_PATCH_STAMP="${CASE_DIR}/work/.altera_lnsim_vcs_patch.stamp"
  PATCH_ID="vcs-skew-v2"
  mkdir -p "${CASE_DIR}/work"
  if [[ ! -f "${LNSIM_PATCH_ID}" ]] || [[ "$(cat "${LNSIM_PATCH_ID}")" != "${PATCH_ID}" ]] \
    || [[ "${ALTERA_LNSIM_SRC}" -nt "${LNSIM_PATCH_STAMP}" ]] || [[ ! -f "${WORK_LNSIM}" ]]; then
    echo "INFO: patch altera_axi4lite_mm_manager for VCS (local work copy)"
    sed '/interface altera_axi4lite_mm_manager/,/endinterface: altera_axi4lite_mm_manager/{
      /clocking m_cb @(posedge clk);/a\
\t\tdefault input #1step;\
\t\tdefault output negedge #1step;
      /STEP 3 IF ARVALID AND ARREADY HIGH/,/drive_zeros_raddr_ch();/{
        /drive_zeros_raddr_ch();/i\
\t\t\t@(posedge clk);
      }
      /STEP 3 IF AWVALID AND AWREADY HIGH/,/drive_zeros_waddr_ch();/{
        /drive_zeros_waddr_ch();/i\
\t\t\t@(posedge clk);
      }
    }' "${ALTERA_LNSIM_SRC}" > "${WORK_LNSIM}"
    echo "${PATCH_ID}" > "${LNSIM_PATCH_ID}"
    touch "${LNSIM_PATCH_STAMP}"
  fi
  ALTERA_LNSIM="${WORK_LNSIM}"

  if [[ ! -f "${HARNESS_SV}" ]]; then
    echo "error: synthesis harness not found at ${HARNESS_SV}" >&2
    exit 1
  fi
  if [[ ! -f "${INPUT_MD}" ]]; then
    echo "error: markdown input not found at ${INPUT_MD}" >&2
    exit 1
  fi

  echo "INFO: generate csr_registers.sv from ${INPUT_MD}"
  "${CSR_GEN}" generate \
    --input-file "${INPUT_MD}" \
    --input-format markdown \
    --markdown-section "${SECTION}" \
    --output-file "${CASE_DIR}/csr_registers.sv" \
    --output-format systemverilog

  echo "INFO: remove prior VCS outputs"
  rm -rf "${SIMV}" "${CASE_DIR}/simv.daidir" "${CASE_DIR}/csrc" \
    "${CASE_DIR}/ucli.key" "${CASE_DIR}/vc_hdrs.h" "${SIM_LOG}"

  VCS_SIM_DIR="${REPO_ROOT}/tests/end2end/commercial_eda/vcs_sim"

  echo "INFO: compile with VCS (altera_axi4lite_mm_manager from ${QUARTUS_SIM_LIB})"
  cd "${CASE_DIR}"
  vcs -full64 -sverilog -timescale=1ps/1ps \
    +incdir+${VCS_SIM_DIR} \
    -top csr_sim_tb \
    -o "${SIMV}" \
    "${ALTERA_LNSIM}" \
    "${CASE_DIR}/csr_registers.sv" \
    "${HARNESS_SV}" \
    "${CASE_DIR}/csr_sim_tb.sv"

  echo "INFO: run ${SIMV}"
  "${SIMV}" | tee "${SIM_LOG}"

  if ! grep -Fq "${PASS_MARKER}" "${SIM_LOG}"; then
    echo "error: simulation did not report success (${PASS_MARKER})" >&2
    exit 1
  fi

  echo "INFO: vcs simulation passed (${CASE_NAME})"
}
