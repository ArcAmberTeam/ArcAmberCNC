"""Prepare the public halcompile module; installation is a separate command."""
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
OUTPUT = PACKAGE.parent / ".build/homing"
OUTPUT.mkdir(parents=True, exist_ok=True)
template = (PACKAGE / "zhulong_homing.comp").read_text()
(OUTPUT / "zhulong_homing.comp").write_text(template.replace('#include "homing.c"', (PACKAGE / "src/homing.c").read_text()))
print(OUTPUT / "zhulong_homing.comp")
