"""Exercise the native source layout and upstream build interfaces.

Archive fixtures verify that HAL and drivers are self-contained under src/hal.
Tests never start a compiler, controller, or hardware.
"""

import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOTS = ("src/hal", "src/hal/drivers", "src/hal/user_comps")


class NativeLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w", dereference=False) as bundle:
            for name in ("src/hal", "src/Makefile"):
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

    def test_archived_sources_use_physical_upstream_paths(self):
        for source_root in SOURCE_ROOTS:
            with self.subTest(source_root=source_root):
                self.assertTrue((ROOT / source_root).is_dir())
                self.assertFalse((ROOT / source_root).is_symlink())
                self.assertTrue((self.work / source_root).is_dir())
                self.assertFalse((self.work / source_root).is_symlink())
        for previous_owner in ("c.hal", "c.drivers", "cpp.drivers"):
            self.assertFalse((ROOT / previous_owner).exists())
            self.assertFalse((ROOT / previous_owner).is_symlink())
        for name in (
            "hal.h", "hal_priv.h", "drivers/hal_pi_gpio.c",
            "drivers/mesa-hostmot2/modbus/modcompile.py",
            "user_comps/mb2hal/mb2hal.c", "user_comps/wj200_vfd/wj200_vfd.comp",
            "user_comps/xhc-hb04.cc", "user_comps/xhc-whb04b-6/hal.cc",
        ):
            with self.subTest(source=name):
                path = self.work / "src/hal" / name
                self.assertTrue(path.is_file())
                self.assertEqual(path.resolve(), path)
        for path in (self.work / "src/hal").rglob("*"):
            if path.is_symlink():
                self.assertTrue(path.exists(), f"Broken source link: {path}")
                self.assertTrue(path.resolve().is_relative_to(self.work / "src/hal"))

    def test_make_resolves_headers_and_both_driver_languages(self):
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
        recipe = source.split("pycheck-python-files:\n", 1)[1].split(
            "\npycheck-python-script:", 1,
        )[0]
        return self.make(
            "pycheck-python-files:\n" + recipe,
            "pycheck-python-files",
        )

    def test_python_scan_reports_errors_in_hal_and_driver_directories(self):
        valid = self.pycheck()
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        for source_root in SOURCE_ROOTS:
            with self.subTest(source_root=source_root):
                probe = self.work / source_root / "layout-invalid-probe.py"
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

    def test_native_snapshot_uses_physical_sources_after_unstaged_moves(self):
        repo = self.work / "snapshot-repo"
        (repo / "src").mkdir(parents=True)
        (repo / "c.hal").mkdir()
        (repo / "frontend").mkdir()
        (repo / "c.hal/hal.h").write_text("/* HAL interface */\n")
        (repo / "src/hal").symlink_to("../c.hal", target_is_directory=True)
        (repo / "frontend/removed.txt").write_text("retired Web source\n")
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        (repo / "src/hal").unlink()
        (repo / "c.hal").rename(repo / "src/hal")
        (repo / "frontend/removed.txt").unlink()
        result = subprocess.run(
            [sys.executable, str(ROOT / ".github/ci/native-source-files.py"), str(repo)],
            check=True, stdout=subprocess.PIPE,
        )
        self.assertEqual(
            set(result.stdout.split(b"\0")) - {b""},
            {b"src/hal/hal.h"},
        )


if __name__ == "__main__":
    unittest.main()
