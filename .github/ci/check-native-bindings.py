"""Smoke-test the freshly compiled public Python API without a HAL session."""

import importlib
import sys
import tempfile
from pathlib import Path

root = Path(sys.argv[1]).resolve()
for name in ("linuxcnc", "gcode", "_hal"):
    module = importlib.import_module(name)
    path = Path(module.__file__).resolve()
    if not path.is_relative_to(root):
        raise RuntimeError(f"{name} imported outside the current build: {path}")
    print(f"Imported {name}: {path}")

import gcode
import linuxcnc

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "machine.ini"
    path.write_text(
        "[KINS]\nJOINTS = 3\n[HAL]\nHALFILE = first.hal\nHALFILE = second.hal\n"
    )
    ini = linuxcnc.ini(str(path))
    assert ini.find("KINS", "JOINTS") == "3"
    assert ini.findall("HAL", "HALFILE") == ["first.hal", "second.hal"]
assert callable(linuxcnc.stat)
assert callable(linuxcnc.command)
assert callable(gcode.parse)
# strerror requires an interpreter created by parse(); importing the extension
# deliberately does not initialize one or open a machine's tool/status channels.
assert callable(gcode.strerror)
print("Native Python imports and INI API passed without opening control channels.")
