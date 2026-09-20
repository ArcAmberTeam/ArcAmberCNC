#!/bin/bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
actionlint -shellcheck= -pyflakes=
shellcheck .github/ci/*.sh .github/staging/*.sh
for script in .github/ci/*.sh .github/staging/*.sh; do bash -n "$script"; done
node --check share/axis/images/toolbar-source/render.cjs
python3 .github/scripts/test-package-version.py
python3 - <<'PY'
import ast
import os
from pathlib import Path
import re
import subprocess

base = os.environ.get("BASE_SHA", "")
if not re.fullmatch(r"[0-9a-f]{40}", base) or base == "0" * 40:
    base = "HEAD^"
base = subprocess.check_output(["git", "merge-base", base, "HEAD"], text=True).strip()
subprocess.run(["git", "diff", "--check", base, "HEAD"], check=True)
changed = subprocess.check_output(
    ["git", "diff", "--name-only", "--diff-filter=ACMR", "-z", base, "HEAD"]
).decode().split("\0")
files = set(Path(".github").rglob("*.py"))
files.update(Path(name) for name in changed if name.endswith(".py"))
for path in sorted(files):
    ast.parse(path.read_bytes(), filename=str(path))
print(f"Python syntax checked: {len(files)} files; diff whitespace/conflicts checked.")
PY
