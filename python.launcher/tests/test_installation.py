"""Stage the real CMake install without writing to the host installation."""

import configparser
import importlib.metadata
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class InstallationTests(unittest.TestCase):
    def test_installed_launcher_has_no_runtime_dependencies(self):
        self.assertFalse(importlib.metadata.requires("betterlinuxcnc-launcher"))

    def test_staged_install_includes_autostart_unit_and_preserves_project_config(self):
        source = Path(__file__).resolve().parents[2] / "python.desktop"
        with tempfile.TemporaryDirectory(prefix="launcher-install-") as temporary:
            root = Path(temporary)
            stage = root / "stage"
            config = stage / "opt/arcambercnc/launcher.json"
            config.parent.mkdir(parents=True)
            config.write_text('{"ini":"keep-existing.ini"}')
            build = root / "build"
            result = subprocess.run(
                [
                    "cmake",
                    "-S",
                    str(source),
                    "-B",
                    str(build),
                    "-DBUILD_TESTING=OFF",
                    "-DCMAKE_INSTALL_PREFIX=/usr",
                    "-DCMAKE_INSTALL_LIBDIR=lib",
                    "-DBETTERCNC_PROJECT_DIR=/opt/arcambercnc",
                    f"-DPython3_EXECUTABLE={sys.executable}",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run(
                ["cmake", "--install", str(build)],
                env=dict(os.environ, DESTDIR=str(stage)),
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(config.read_text(), '{"ini":"keep-existing.ini"}')
            self.assertTrue((config.parent / "launcher.example.json").is_file())
            unit = stage / "usr/lib/systemd/user/betterlinuxcnc-launcher.service"
            parser = configparser.ConfigParser(interpolation=None)
            parser.read(unit)
            self.assertEqual(parser["Service"]["Restart"], "on-failure")
            self.assertIn("SIGKILL", parser["Service"]["RestartPreventExitStatus"])
            self.assertIn("78", parser["Service"]["RestartPreventExitStatus"])
            self.assertEqual(parser["Service"]["KillMode"], "process")
            self.assertIn("/opt/arcambercnc/launcher.json", parser["Service"]["ExecStart"])
            parser.read(stage / "etc/xdg/autostart/betterlinuxcnc-autostart.desktop")
            self.assertIn("--session-start", parser["Desktop Entry"]["Exec"])
            self.assertNotEqual(parser["Desktop Entry"].get("Hidden"), "true")
            parser.read(stage / "usr/share/applications/betterlinuxcnc-qt.desktop")
            self.assertEqual(
                parser["Desktop Entry"]["Exec"], "betterlinuxcnc-launch --session-start"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(stage / "usr/bin/betterlinuxcnc-launch"),
                    "--help",
                ],
                env=dict(os.environ, PYTHONPATH=str(stage / "usr/lib/betterlinuxcnc/python")),
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--config", result.stdout)
            # Verify the generated unit using the host's offline parser where
            # available; substitute only the not-yet-installed executable path.
            analyzer = shutil.which("systemd-analyze")
            if analyzer:
                checked = root / "betterlinuxcnc-launcher.service"
                checked.write_text(
                    unit.read_text().replace('"/usr/bin/betterlinuxcnc-launch"', '"/bin/true"')
                )
                result = subprocess.run(
                    [analyzer, "--user", "verify", str(checked)],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
