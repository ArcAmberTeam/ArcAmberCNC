#!/usr/bin/env python3
"""Enforce named QML module imports and the declared capability graph."""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULES = ROOT / "qml" / "BetterCnc"
ALLOWED = {
    "Ui": set(),
    "Catalog": set(),
    "Manual": {"Ui", "Catalog"},
    "Toolpath": {"Ui", "Catalog"},
    "Program": {"Ui", "Catalog"},
    "Chrome": {"Ui", "Catalog", "Manual", "Toolpath"},
}
errors = []
for directory in sorted(MODULES.iterdir()):
    if not directory.is_dir():
        continue
    owner = directory.name
    if owner not in ALLOWED:
        errors.append(f"Unregistered module: {owner}")
        continue
    manifest = directory / "qmldir"
    if not manifest.exists():
        errors.append(f"Missing public manifest: {manifest}")
        continue
    declared = set(re.findall(r"\b([\w.-]+\.qml)\b", manifest.read_text()))
    for source in directory.rglob("*.qml"):
        if source.parent == directory and source.name not in declared:
            errors.append(f"Undeclared public/internal type: {source}")
        text = source.read_text()
        for imported in re.findall(r"^import\s+BetterCnc\.([\w.]+)", text, re.M):
            if imported not in ALLOWED[owner] and imported != owner:
                errors.append(f"{source}: forbidden dependency {owner} → {imported}")
        for imported in re.findall(r'^import\s+"([^"]+)"', text, re.M):
            target = (source.parent / imported).resolve()
            if not target.is_relative_to(directory.resolve()):
                errors.append(f"{source}: cross-module private import {imported}")
        for imported in re.findall(
            r'Qt\.(?:createComponent|resolvedUrl)\(\s*[\'"]([^\'"]+)[\'"]', text
        ):
            target = (source.parent / imported).resolve()
            if not target.is_relative_to(directory.resolve()):
                errors.append(f"{source}: cross-module private resource {imported}")
        if re.search(r"^import\s+(QtWebEngine|QtWebView|QtNetwork)", text, re.M):
            errors.append(f"{source}: platform access in a presentation module")
        if re.search(r"\b(XMLHttpRequest|WebSocket)\b", text):
            errors.append(f"{source}: network access in a presentation module")

for source in (ROOT / "qml").glob("*.qml"):
    if re.search(r'^import\s+".*BetterCnc/', source.read_text(), re.M):
        errors.append(f"{source}: composition must use named public modules")

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
print(f"QML boundaries passed ({len(ALLOWED)} modules).")
