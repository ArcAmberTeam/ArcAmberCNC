"""Guard the retired GUI boundary through build targets and the launcher CLI.

These tests do not compile LinuxCNC or connect to a controller.
"""

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class NativeAxisRemovalTests(unittest.TestCase):
    def test_native_application_is_absent_and_web_assets_are_owned_locally(self):
        for name in (
            "src/emc/usr_intf/axis", "share/axis", "bin/profile_axis",
            "lib/python/propertywindow.py", "docs/man/man1/axis.1",
            "docs/man/man1/axis-remote.1",
        ):
            with self.subTest(name=name):
                self.assertFalse((ROOT / name).exists())
        for name in ("tool_run.gif", "tool_stop.gif", "NOTICE.md", "TOOLBAR-LICENSE"):
            self.assertTrue((ROOT / "frontend/public/axis" / name).is_file())

    def test_install_manifests_do_not_ship_the_retired_gui(self):
        for name in (
            "src/Makefile", "debian/linuxcnc.install.in",
            "debian/linuxcnc.manpages.in", "debian/linuxcnc-doc-en.docs",
        ):
            content = (ROOT / name).read_text()
            with self.subTest(name=name):
                self.assertNotRegex(content, r"emc/usr_intf/axis|share/axis|README\.axis")
                self.assertNotRegex(content, r"bin/axis(?:-remote)?(?:\s|$)")
                self.assertNotRegex(content, r"man1/axis(?:-remote)?\.1")
        manifest = (ROOT / "debian/linuxcnc.install.in").read_text()
        self.assertIn("usr/share/linuxcnc/tk-support/", manifest)

    def make_dry_run(self, target):
        with tempfile.TemporaryDirectory(prefix="linuxcnc-make-") as directory:
            work = Path(directory) / "src"
            work.mkdir()
            (work / "emc").symlink_to(ROOT / "src/emc", target_is_directory=True)
            # Supply the parent build's object rules without a Linux toolchain.
            (work / "Makefile").write_text("""
TOOBJS = $(addprefix objects/,$(addsuffix .o,$(basename $(1))))
TOOBJSDEPS = $(call TOOBJS,$(1))
CXX = c++
CC = cc
PYTHON = python3
ECHO = echo
include emc/usr_intf/python-interface/Submakefile
include emc/usr_intf/python-tools/Submakefile
include emc/usr_intf/tk-support/Submakefile
.PHONY: all
all: $(PYTARGETS)
objects/%.o: %.cc
\t$(CXX) -c $< -o $@
objects/%.o: %.c
\t$(CC) -c $< -o $@
Makefile.inc ../lib/liblinuxcnc.a ../lib/libnml.so.0 ../lib/liblinuxcncini.so ../lib/libtooldata.so.0:
""")
            result = subprocess.run(
                ["make", "-r", "-n", target], cwd=work,
                text=True, capture_output=True, timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout

    def test_python_control_binding_build_does_not_require_a_tk_display(self):
        output = self.make_dry_run("../lib/python/linuxcnc.so")
        self.assertIn("emc/usr_intf/python-interface/emcmodule.cc", output)
        self.assertIn("-shared -o ../lib/python/linuxcnc.so", output)
        self.assertNotIn("_togl", output)
        self.assertNotIn("../bin/axis", output)

    def test_retained_tools_and_togl_still_have_build_targets(self):
        output = self.make_dry_run("all")
        for command in ("hal_manualtoolchange", "mdi", "linuxcnctop", "image-to-gcode"):
            with self.subTest(command=command):
                self.assertIn("../bin/" + command, output)
        self.assertIn("emc/usr_intf/tk-support/_toglmodule.c", output)
        self.assertNotIn("../bin/axis", output)

    def test_legacy_display_is_rejected_before_controller_processes_start(self):
        # Exercise the complete launcher, substituting only configure values
        # and external commands. No machine commands or user files are touched.
        with tempfile.TemporaryDirectory(prefix="linuxcnc-launcher-") as directory:
            work = Path(directory)
            bindir = work / "bin"
            bindir.mkdir()
            inivar = bindir / "inivar"
            inivar.write_text("""#!/usr/bin/env python3
import configparser
import sys
args = sys.argv[1:]
config = configparser.RawConfigParser()
config.read(args[args.index('-ini') + 1])
try:
    print(config.get(args[args.index('-sec') + 1], args[args.index('-var') + 1]))
except (configparser.Error, ValueError):
    sys.exit(1)
""")
            inivar.chmod(0o755)
            forbidden = bindir / "forbidden"
            forbidden.write_text('#!/bin/sh\nprintf "%s\\n" "$0" >> "$LAUNCH_TRACE"\nexit 99\n')
            forbidden.chmod(0o755)
            for name in ("halcmd", "linuxcncsvr", "milltask", "axis", "axis.py", "realtime"):
                (bindir / name).symlink_to(forbidden)
            values = {
                "RUN_IN_PLACE": "no", "KERNEL_VERS": "", "EMC2_HOME": str(work),
                "EMC2_BIN_DIR": str(bindir), "GREP": shutil.which("grep"),
                "TCLSH": "true", "WISH": "true", "EMC2VERSION": "2.9.10",
            }
            template = (ROOT / "scripts/linuxcnc.in").read_text()
            launcher = work / "linuxcnc"
            launcher.write_text(re.sub(
                r"@([A-Za-z0-9_]+)@", lambda m: values.get(m[1], str(work)), template,
            ))
            trace = work / "calls"
            env = dict(os.environ, DISPLAY=":test", LAUNCH_TRACE=str(trace))
            for display in ("axis", "axis -geometry 1024x768", str(bindir / "axis"),
                            "axis.py", str(bindir / "axis.py")):
                with self.subTest(display=display):
                    ini = work / "machine.ini"
                    ini.write_text(
                        "[EMC]\nVERSION = 1.1\n[RS274NGC]\nPARAMETER_FILE = test.var\n"
                        "[TASK]\nTASK = milltask\n[DISPLAY]\nDISPLAY = " + display + "\n"
                    )
                    result = subprocess.run(
                        ["bash", str(launcher), "-r", str(ini)], cwd=work, env=env,
                        text=True, capture_output=True, timeout=15,
                    )
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn("native AXIS GUI has been removed", result.stderr)
                    self.assertIn("static prototype", result.stderr)
                    self.assertFalse(trace.exists(), trace.read_text() if trace.exists() else "")


if __name__ == "__main__":
    unittest.main()
