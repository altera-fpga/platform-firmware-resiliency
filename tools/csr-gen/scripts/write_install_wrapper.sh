#!/usr/bin/env bash
# Write a small wrapper script that exec's a binary from ../venv/bin/.
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: write_install_wrapper.sh <wrapper-path> <venv-executable-name>" >&2
  exit 1
fi

wrapper_path="$1"
executable_name="$2"
wrapper_dir="$(dirname "$wrapper_path")"
mkdir -p "$wrapper_dir"

cat >"$wrapper_path" <<EOF
#!/usr/bin/env bash
set -euo pipefail
HERE="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
exec "\$HERE/../venv/bin/${executable_name}" "\$@"
EOF

chmod +x "$wrapper_path"
