"""Exercise native build interfaces across physical module source ownership.

Archive fixtures verify that relative links do not borrow files from the
original checkout. Tests never start a compiler, controller, or hardware.
"""

import io
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
OWNERS = ("c.hal", "c.drive", "cpp.drive")


class NativeLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w", dereference=False) as bundle:
            for name in (*OWNERS, "src/hal", "src/Makefile"):
                bundle.add(ROOT / name, arcname=name)
        cls.archive = archive.getvalue()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="linuxcnc-native-layout-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name).resolve()
        with tarfile.open(fileobj=io.BytesIO(self.archive)) as bundle:
            # This is an archive made above from named local source roots.
            # Validate members also on older Pythons without extraction filters.
            for member in bundle.getmembers():
                path = self.work / member.name
                self.assertTrue(path.resolve().is_relative_to(self.work))
                if member.issym():
                    self.assertTrue(
                        (path.parent / member.linkname).resolve().is_relative_to(self.work),
                    )
            options = {"filter": "data"} if hasattr(tarfile, "data_filter") else {}
            bundle.extractall(self.work, **options)

    def make(self, rules, *targets):
        makefile = self.work / "src/layout-test.mk"
        makefile.write_text("SHELL := /bin/bash\n" + rules)
        return subprocess.run(
            ["make", "-r", "-f", str(makefile), *targets],
            cwd=self.work / "src", text=True, capture_output=True, timeout=30,
            env=dict(os.environ, PYTHONPYCACHEPREFIX=str(self.work / "pycache")),
        )

    def test_archived_legacy_paths_keep_one_physical_source_owner(self):
        paths = {
            "src/hal/hal.h": "c.hal/hal.h",
            "src/hal/utils/../hal_priv.h": "c.hal/hal_priv.h",
            "src/hal/drivers/hal_pi_gpio.c": "c.drive/hal_pi_gpio.c",
            "src/hal/drivers/mesa-hostmot2/modbus/modcompile.py":
                "c.drive/mesa-hostmot2/modbus/modcompile.py",
            "src/hal/user_comps/mb2hal/mb2hal.c":
                "c.drive/user/mb2hal/mb2hal.c",
            "src/hal/user_comps/wj200_vfd/wj200_vfd.comp":
                "c.drive/user/wj200_vfd/wj200_vfd.comp",
            "src/hal/user_comps/xhc-hb04.cc":
                "cpp.drive/pendant/xhc-hb04.cc",
            "src/hal/user_comps/xhc-whb04b-6/hal.cc":
                "cpp.drive/pendant/xhc-whb04b-6/hal.cc",
        }
        for legacy, owner in paths.items():
            with self.subTest(legacy=legacy):
                self.assertTrue((self.work / legacy).is_file())
                self.assertEqual(
                    (self.work / legacy).resolve(), (self.work / owner).resolve(),
                )
        self.assertTrue((self.work / "src/hal").is_symlink())
        for owner in OWNERS:
            self.assertFalse((self.work / owner).is_symlink())
        for directory in ("c.hal", "c.hal/user_comps"):
            for path in (self.work / directory).iterdir():
                if path.is_symlink():
                    self.assertTrue(path.exists(), f"Broken build link: {path}")
                    self.assertTrue(path.resolve().is_relative_to(self.work))

    def test_make_can_export_headers_and_compile_both_driver_languages(self):
        result = self.make("""
TOOBJS = $(addprefix objects/,$(addsuffix .o,$(basename $(1))))
TOOBJSDEPS = $(call TOOBJS,$(1))
BUILD_SYS = uspace
HAVE_LIBMODBUS3 = 1
HAVE_LIBUSB10 = 1
CC = cc
CXX = c++
PYTHON = python3
ECHO = echo
include hal/Submakefile
include hal/drivers/mesa-hostmot2/Submakefile
include hal/user_comps/Submakefile
include hal/user_comps/mb2hal/Submakefile
include hal/user_comps/xhc-whb04b-6/Submakefile
objects/%.o: %.cc
\t$(CXX) -c $< -o $@
objects/%.o: %.c
\t$(CC) -c $< -o $@
../lib/liblinuxcncini.so.0:
""", "-n", "../include/hal.h", "../include/hostmot2-serial.h",
            "../bin/gs2_vfd", "../bin/xhc-whb04b-6")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for source in (
            "hal/hal.h", "hal/drivers/mesa-hostmot2/hostmot2-serial.h",
            "hal/user_comps/gs2_vfd.c", "hal/user_comps/xhc-whb04b-6/hal.cc",
        ):
            self.assertIn(source, result.stdout)

    def pycheck(self):
        source = (self.work / "src/Makefile").read_text()
        source_dirs = re.search(r"^HAL_SOURCE_DIRS := .+$", source, re.MULTILINE)
        self.assertIsNotNone(source_dirs)
        recipe = source.split("pycheck-python-files:\n", 1)[1].split(
            "\npycheck-python-script:", 1,
        )[0]
        return self.make(
            source_dirs[0] + "\npycheck-python-files:\n" + recipe,
            "pycheck-python-files",
        )

    def test_python_scan_reports_errors_in_each_relocated_owner(self):
        valid = self.pycheck()
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        for owner in OWNERS:
            with self.subTest(owner=owner):
                probe = self.work / owner / "layout-invalid-probe.py"
                probe.write_text("def invalid(:\n")
                try:
                    invalid = self.pycheck()
                    self.assertNotEqual(invalid.returncode, 0)
                    self.assertIn("layout-invalid-probe.py", invalid.stderr)
                    self.assertIn("SyntaxError", invalid.stderr)
                finally:
                    probe.unlink()
        restored = self.pycheck()
        self.assertEqual(restored.returncode, 0, restored.stdout + restored.stderr)

    def test_native_snapshot_uses_working_tree_owners_after_unstaged_moves(self):
        repo = self.work / "snapshot-repo"
        (repo / "src/hal").mkdir(parents=True)
        (repo / "frontend").mkdir()
        (repo / "src/hal/hal.h").write_text("/* HAL interface */\n")
        (repo / "frontend/removed.txt").write_text("retired Web source\n")
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        (repo / "src/hal").rename(repo / "c.hal")
        (repo / "src/hal").symlink_to("../c.hal", target_is_directory=True)
        (repo / "frontend/removed.txt").unlink()
        result = subprocess.run(
            [sys.executable, str(ROOT / ".github/ci/native-source-files.py"), str(repo)],
            check=True, stdout=subprocess.PIPE,
        )
        self.assertEqual(
            set(result.stdout.split(b"\0")) - {b""},
            {b"c.hal/hal.h", b"src/hal"},
        )


if __name__ == "__main__":
    unittest.main()
