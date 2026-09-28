#!/bin/bash
# Prepare the Makefile dry-run tests on the persistent Debian/Ubuntu runner.
set -euo pipefail

if command -v make >/dev/null 2>&1; then
  make --version
  exit 0
fi

as_root=()
if (( EUID != 0 )); then
  as_root=(sudo -n)
fi

"${as_root[@]}" apt-get update
"${as_root[@]}" apt-get install --yes --no-install-recommends make
make --version
