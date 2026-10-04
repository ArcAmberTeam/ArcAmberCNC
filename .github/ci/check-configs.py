"""Static checks only: never execute HAL, Tcl, loadrt, loadusr or a machine INI.

Legacy diagnostics are matched exactly against an explicit, reviewed baseline.
Dynamic paths and runtime pin existence require target-machine validation.
"""

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path


def logical_lines(text):
    pending = ""
    start = 1
    for number, line in enumerate(text.splitlines(), 1):
        if not pending:
            start = number
        if line.rstrip().endswith("\\"):
            pending += line.rstrip()[:-1] + " "
            continue
        yield start, pending + line
        pending = ""
    if pending:
        yield start, pending + "\\"


def inspect(root):
    issues = []
    count = 0
    includes = {}

    def issue(path, line, message):
        issues.append(f"{path.relative_to(root)}:{line}: {message}")

    def reference(path, number, value, *, include=False):
        try:
            words = shlex.split(value, comments=True)
        except ValueError as error:
            issue(path, number, str(error))
            return
        if not words:
            return
        name = words[0]
        if name in ("WORKING", "None", "none") or any(c in name for c in "$[~"):
            return
        if Path(name).is_absolute():
            return
        if name.startswith("LIB:"):
            candidates = [root / "lib/hallib" / name[4:]]
        else:
            candidates = [
                path.parent / name,
                root / "configs/common" / name,
                root / "lib/hallib" / name,
            ]
        target = next((p for p in candidates if p.is_file()), None)
        if target is None:
            issue(path, number, f"missing local reference: {name}")
        elif include:
            includes.setdefault(path.resolve(), []).append(target.resolve())

    # Scan configuration sources and shared HAL libraries, including INI fragments.
    paths = sorted(
        {
            p
            for folder in (root / "configs", root / "lib/hallib")
            for p in folder.rglob("*")
            if p.suffix in (".ini", ".inc", ".hal", ".tcl")
        }
    )
    for path in paths:
        count += 1
        if not path.is_file():
            issue(path, 1, "broken configuration symlink")
            continue
        try:
            text = path.read_text()
        except UnicodeError:
            # Some inherited example comments use Latin-1; HAL tokens are ASCII.
            text = path.read_text(encoding="latin-1")
        if "\0" in text:
            issue(path, 1, "NUL byte in configuration")
        if re.search(r"^(?:<<<<<<< |=======\s*$|>>>>>>> )", text, re.MULTILINE):
            issue(path, 1, "unresolved merge conflict")
        if path.suffix == ".tcl":
            # Tcl's parser checks balanced syntax without evaluating any command.
            result = subprocess.run(
                ["tclsh"],
                input="set f [open $::env(CI_TCL_FILE) r]\n"
                "set s [read $f]\nclose $f\nputs [info complete $s]\n",
                env={**os.environ, "CI_TCL_FILE": str(path)},
                text=True,
                capture_output=True,
                check=True,
                timeout=10,
            )
            if result.stdout.strip() != "1":
                issue(path, 1, "incomplete Tcl syntax")
            continue
        section = ""
        for number, raw in logical_lines(text):
            line = raw.strip()
            if path.suffix in (".ini", ".inc") and line.startswith("#INCLUDE"):
                reference(path, number, line[len("#INCLUDE") :].strip(), include=True)
                continue
            if not line or line.startswith(("#", ";")):
                continue
            if line.endswith("\\"):
                issue(path, number, "unfinished line continuation")
            if path.suffix in (".ini", ".inc"):
                header = re.match(r"^\[([^\]]+)\]", line)
                if header:
                    section = header[1].upper()
                    continue
                if "=" not in line or not section:
                    issue(path, number, f"invalid INI assignment: {line}")
                    continue
                key, value = line.split("=", 1)
                if not key.strip():
                    issue(path, number, "empty INI key")
                if section == "HAL" and key.strip().upper() in (
                    "HALFILE",
                    "POSTGUI_HALFILE",
                    "SHUTDOWN",
                ):
                    reference(path, number, value)
            else:
                try:
                    words = shlex.split(line, comments=True)
                except ValueError as error:
                    issue(path, number, str(error))
                    continue
                if not words:
                    continue
                minimum = {
                    # halcmd accepts an existing signal without additional pins.
                    "net": 2,
                    "setp": 3,
                    "sets": 3,
                    "addf": 3,
                    "loadrt": 2,
                    "loadusr": 2,
                    "newsig": 3,
                    "source": 2,
                    "linkps": 3,
                    "linksp": 3,
                    "linkpp": 3,
                }
                if len(words) < minimum.get(words[0], 1):
                    issue(path, number, f"too few arguments: {line}")
                if words[0] == "source" and len(words) > 1:
                    reference(path, number, shlex.quote(words[1]), include=True)

    def visit(node, active):
        if node in active:
            issue(node, 1, "configuration include cycle")
            return
        for child in includes.get(node, []):
            visit(child, active | {node})

    for node in includes:
        visit(node, set())
    return count, sorted(set(issues))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    baseline_path = args.baseline or root / ".github/ci/config-baseline.json"
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {}
    count, issues = inspect(root)
    accepted = {
        item
        for item, record in baseline.items()
        if (root / item.split(":", 1)[0]).is_file()
        and hashlib.sha256((root / item.split(":", 1)[0]).read_bytes()).hexdigest()
        == record["sha256"]
    }
    if not count:
        parser.error("No configuration files found")
    if args.json:
        print(json.dumps(issues, indent=2, ensure_ascii=False))
    else:
        for item in issues:
            print(f"{'LEGACY' if item in accepted else 'ERROR'} {item}")
        for item in sorted(set(baseline) - set(issues)):
            print(f"ERROR stale baseline entry (remove it): {item}")
        print(
            f"Checked {count} configuration files; {len(issues)} diagnostics, "
            f"{len(set(issues) - accepted)} new. No configuration executed."
        )
    return int(set(issues) != accepted or set(issues) != set(baseline))


if __name__ == "__main__":
    sys.exit(main())
