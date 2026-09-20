#!/bin/bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
.github/ci/bootstrap-base.sh
# Cache only packaging dependencies, never application build outputs.
tar -cf - .github/ci/Dockerfile debian |
  docker build -f .github/ci/Dockerfile -t betterlinuxcnc-ci:trixie -
