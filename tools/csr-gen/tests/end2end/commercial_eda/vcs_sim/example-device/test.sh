#!/usr/bin/env bash
# Compile and run example-device CSR functional simulation with VCS.
set -euo pipefail

CASE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=../common.sh
source "${CASE_DIR}/../common.sh"
run_vcs_sim
