#!/usr/bin/env bash
# Compile and run cca-accel CSR functional simulation with VCS.
set -euo pipefail

CASE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${CASE_DIR}/../../../../.." && pwd)
export INPUT_MD="${REPO_ROOT}/tests/testdata/cca_accel.md"
# shellcheck source=../common.sh
source "${CASE_DIR}/../common.sh"
run_vcs_sim
