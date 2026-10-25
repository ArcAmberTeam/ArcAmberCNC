"""Stage the real CMake install without writing to the host installation."""

import configparser
import importlib.metadata
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


class InstallationTests(unittest.TestCase):
    def test_installed_launcher_has_no_runtime_dependencies(self):
        self.assertFalse(importlib.metadata.requires("betterlinuxcnc-launcher"))

    def test_standalone_desktop_installs_only_its_own_application(self):
        source = Path(__file__).resolve().parents[3] / "app/desktop"
        with tempfile.TemporaryDirectory(prefix="desktop-install-") as temporary:
            root = Path(temporary)
            build = root / "build"
            stage = root / "stage"
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
                    f"-DPython3_EXECUTABLE={sys.executable}",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Building the desktop only", result.stdout)
            result = subprocess.run(
                ["cmake", "--install", str(build)],
                env=dict(os.environ, DESTDIR=str(stage)),
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(
                {path.name for path in (stage / "usr/bin").iterdir()},
                {"betterlinuxcnc"},
            )
            self.assertEqual(
                {path.name for path in (stage / "usr/lib/betterlinuxcnc/python").iterdir()},
                {"bettercnc"},
            )
            self.assertTrue((stage / "usr/share/betterlinuxcnc/qml/Main.qml").is_file())
            self.assertFalse((stage / "usr/lib/systemd").exists())
            self.assertFalse((stage / "etc").exists())

    def assert_debian_release_package(self, source, build, stage, output):
        result = subprocess.run(
            ["cpack", "--config", str(build / "CPackConfig.cmake"), "-G", "DEB", "-B", str(output)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        packages = list(output.glob("*.deb"))
        self.assertEqual(len(packages), 1)
        package = packages[0]
        unpacked = output / "unpacked"
        result = subprocess.run(
            ["dpkg-deb", "--extract", str(package), str(unpacked)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("betterlinuxcnc-cam-link", "betterlinuxcnc-updater"):
            with self.subTest(packaged_command=command):
                self.assertEqual(
                    (unpacked / "usr/bin" / command).read_bytes(),
                    (stage / "usr/bin" / command).read_bytes(),
                )
        fields = {}
        for field in ("Package", "Version", "Architecture", "Depends"):
            result = subprocess.run(
                ["dpkg-deb", "--field", str(package), field],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            fields[field] = result.stdout.strip()
        with (source / "app/desktop/pyproject.toml").open("rb") as metadata:
            application_version = tomllib.load(metadata)["project"]["version"]
        architecture = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()
        self.assertEqual(fields["Package"], "betterlinuxcnc-qt")
        self.assertEqual(fields["Version"], application_version)
        self.assertEqual(fields["Architecture"], architecture)
        self.assertEqual(
            package.name,
            f"betterlinuxcnc-qt_{fields['Version']}_{fields['Architecture']}.deb",
        )
        dependencies = {entry.strip().split()[0] for entry in fields["Depends"].split(",")}
        self.assertTrue(
            {"pkexec", "ca-certificates", "apt", "dpkg", "dbus-user-session"} <= dependencies,
            dependencies,
        )

    def test_staged_install_includes_autostart_unit_and_preserves_project_config(self):
        source = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory(prefix="launcher-install-") as temporary:
            root = Path(temporary)
            stage = root / "stage"
            config = stage / "opt/arcambercnc/launcher.json"
            config.parent.mkdir(parents=True)
            config.write_text('{"ini":"keep-existing.ini"}')
            retired_cam = stage / "usr/lib/betterlinuxcnc/python/bettercnc_cam_link"
            retired_cam.mkdir(parents=True)
            (retired_cam / "__init__.py").write_text("# obsolete Python CAM service\n")
            build = root / "build"
            # Reuse an explicitly built target binary for local package verification.
            # CI leaves these unset so both Rust services build from this checkout.
            prebuilt_services = [
                f"-D{name}={os.environ[name]}"
                for name in ("BETTERCNC_CAM_LINK_BINARY", "BETTERCNC_UPDATER_BINARY")
                if os.environ.get(name)
            ]
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
                    *prebuilt_services,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run(
                ["cmake", "--build", str(build), "--parallel"],
                capture_output=True,
                text=True,
                timeout=600,
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
            cam_binary = stage / "usr/bin/betterlinuxcnc-cam-link"
            self.assertFalse(cam_binary.read_bytes().startswith(b"#!"))
            result = subprocess.run(
                [str(cam_binary), "--help"], capture_output=True, text=True, timeout=10
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Rust CAM Link", result.stdout)
            updater_binary = stage / "usr/bin/betterlinuxcnc-updater"
            self.assertFalse(updater_binary.read_bytes().startswith(b"#!"))
            result = subprocess.run(
                [str(updater_binary), "--help"], capture_output=True, text=True, timeout=10
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("betterlinuxcnc-updater", result.stdout)
            python_root = stage / "usr/lib/betterlinuxcnc/python"
            for package in (
                "bettercnc",
                "betterlinuxcnc_service",
                "bettercnc_controller",
                "bettercnc_preview",
                "bettercnc_launcher",
            ):
                with self.subTest(package=package):
                    self.assertTrue((python_root / package / "__init__.py").is_file())
            self.assertFalse((python_root / "bettercnc_cam_link").exists())
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
            if sys.platform.startswith("linux"):
                self.assert_debian_release_package(source, build, stage, root / "packages")
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
