#!/bin/bash
# Debian supplies the native interpreter; this suite owns the Python adapter.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  ca-certificates python3-venv linuxcnc-uspace
preview_venv=$(mktemp -d)
trap 'rm -rf "$preview_venv"' EXIT
python3 -m venv --system-site-packages "$preview_venv"
"$preview_venv/bin/python" -m pip install -r backend/requirements-ci.txt
PYTHON="$preview_venv/bin/python" bash .github/ci/python-check.sh preview
