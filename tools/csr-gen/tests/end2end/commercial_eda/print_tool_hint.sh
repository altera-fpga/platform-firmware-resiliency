#!/usr/bin/env bash
# Print optional local setup notes when a commercial EDA tool is missing.
# The notes file is omitted from public releases.

print_eda_tool_hint() {
  local root="$1"
  local hint="${root}/docs/not_shipped/eda-tool-hint.txt"
  if [[ -f "${hint}" ]]; then
    cat "${hint}" >&2
  fi
}
