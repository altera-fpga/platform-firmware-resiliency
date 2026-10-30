#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"

csr-gen --help >/dev/null

golden_dir="${repo_root}/specs/golden/example-device"
section="$(tr -d '\n' < "${golden_dir}/section.txt")"
csr-gen validate \
  --input-file "${golden_dir}/regs.md" \
  --markdown-section "${section}" \
  --dump-model >/dev/null
