#!/usr/bin/env bash
# Build csr-gen DML as a Simics module and run module tests for example-device.
set -euo pipefail

CASE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=../common.sh
source "${CASE_DIR}/../common.sh"
run_simics_case
