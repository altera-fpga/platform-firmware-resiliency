#!/usr/bin/env bash
# Build csr-gen DML as a Simics module and run module tests for cca-accel.
set -euo pipefail

CASE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${CASE_DIR}/../../../../.." && pwd)
INPUT_MD="${REPO_ROOT}/tests/testdata/cca_accel.md"
export INPUT_MD
# shellcheck source=../common.sh
source "${CASE_DIR}/../common.sh"
run_simics_case
