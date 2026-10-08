#!/bin/bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
actionlint -shellcheck= -pyflakes=
shellcheck .github/ci/*.sh python.desktop/scripts/ci-check.sh
for script in .github/ci/*.sh python.desktop/scripts/ci-check.sh; do bash -n "$script"; done
python3 -m unittest discover -s .github/ci -p 'test_*.py'
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
