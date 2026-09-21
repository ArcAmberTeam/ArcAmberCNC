#!/bin/bash
# Root-owned entry point; never replace it from an uploaded release artifact.
set -euo pipefail
umask 022
[[ $EUID == 0 && $# == 1 && $1 =~ ^[0-9]+-[0-9]+-[0-9a-f]{40}$ ]] || exit 2
# Python isolated mode ignores deploy-controlled environment and import paths.
exec /usr/bin/python3 -I /usr/local/lib/betterlinuxcnc/web_release.py install "$1" \
  --base /srv/betterlinuxcnc-web --health-url http://127.0.0.1:8080
