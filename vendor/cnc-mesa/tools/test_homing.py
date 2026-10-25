from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if not shutil.which("halcompile"):
    raise SystemExit("Install LinuxCNC 2.9 and its development headers (linuxcnc-uspace-dev).")
build = ROOT / ".build/homing"
subprocess.run(["halcompile", "--compile", "zhulong_homing.comp"], cwd=build, check=True)
with tempfile.TemporaryDirectory(prefix="cnc-mesa-home-") as temp:
    binary = Path(temp) / "test_homing"
    subprocess.run([
        # RTAPI module exports are irrelevant to this static public-API harness.
        # The real module above is compiled by halcompile with exports enabled.
        "cc", "-std=gnu11", "-DULAPI", "-DEXPORT_SYMBOL(x)=", "-Wall", "-Wextra",
        "-I/usr/include/linuxcnc", "-I" + str(ROOT / "homing/upstream"),
        str(ROOT / "tests/homing/test_homing.c"),
        str(ROOT / "homing/src/homing.c"),
        str(ROOT / "homing/upstream/simple_tp.c"),
        "-lm", "-o", str(binary),
    ], check=True)
    for axis in range(3):
        for scenario in ("normal", "initially-active", "missing", "stuck", "final-stuck", "cancel", "cancel-retreat", "limit", "wrong-direction"):
            subprocess.run([str(binary), scenario, str(axis)], check=True, timeout=15)
            subprocess.run([str(binary), scenario, str(axis), "negative-xyz"], check=True, timeout=15)
    subprocess.run([
        "cc", "-std=gnu11", "-DULAPI", "-DEXPORT_SYMBOL(x)=", "-Wall", "-Wextra",
        "-I/usr/include/linuxcnc", "-I" + str(ROOT / "homing/upstream"),
        str(ROOT / "tests/homing/test_parallel.c"),
        str(ROOT / "homing/src/homing.c"),
        str(ROOT / "homing/upstream/simple_tp.c"), "-lm", "-o", str(binary),
    ], check=True)
    for axis in range(3):
        for scenario in ("normal", "initially-active", "missing", "stuck", "final-stuck", "cancel", "cancel-retreat", "limit", "invalid-backoff"):
            subprocess.run([str(binary), scenario, str(axis)], check=True, timeout=15)
