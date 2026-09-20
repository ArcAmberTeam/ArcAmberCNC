#!/usr/bin/env python3
"""Exercise changelog generation against real tagged and tagless Git repositories."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[2]


class PackageVersionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="linuxcnc-version-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ("debian", "scripts", "src", "gnupg", "test-bin"):
            (self.root / directory).mkdir()
        for name in ("debian/update-dch-from-git", "scripts/get-version-from-git",
                     "scripts/githelper.sh"):
            shutil.copy2(SOURCE / name, self.root / name)
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="Version test",
                        GIT_AUTHOR_EMAIL="test@example.invalid",
                        GIT_COMMITTER_NAME="Version test",
                        GIT_COMMITTER_EMAIL="test@example.invalid")
        # macOS developers lack Debian's tools. CI uses the real installed tools;
        # local fallbacks only isolate distribution detection/final formatting.
        for name, script in (("lsb_release", "printf 'bookworm\\n'"), ("dch", "exit 0")):
            if shutil.which(name) is None:
                stub = self.root / "test-bin" / name
                stub.write_text("#!/bin/sh\n" + script + "\n")
                stub.chmod(0o755)
        self.env["PATH"] = str(self.root / "test-bin") + os.pathsep + self.env["PATH"]
        (self.root / "VERSION").write_text("2.9.10\n")
        (self.root / "debian/changelog").write_text(
            "linuxcnc (1:2.9.10) unstable; urgency=low\n\n"
            "  * Original release.\n\n"
            " -- Version test <test@example.invalid>  Mon, 21 Sep 2026 00:00:00 +0000\n")
        self.run_command("git", "init", "-q", "-b", "kihon")
        self.run_command("git", "add", ".")
        self.run_command("git", "commit", "-qm", "Initial snapshot")

    def run_command(self, *args):
        return subprocess.run(args, cwd=self.root, env=self.env, check=True,
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def update(self):
        self.run_command("bash", "debian/update-dch-from-git")
        return (self.root / "debian/changelog").read_text()

    def test_tagless_snapshot(self):
        changelog = self.update()
        self.assertIn("linuxcnc (1:2.9.10~kihon~", changelog)
        self.assertIn("  * Initial snapshot", changelog)

    def test_tagless_detached_checkout(self):
        self.run_command("git", "checkout", "--detach", "-q")
        changelog = self.update()
        self.assertIn("linuxcnc (1:2.9.10~head~", changelog)
        self.assertIn("  * Initial snapshot", changelog)

    def test_annotated_tag_limits_history(self):
        self.run_command("git", "tag", "-a", "v2.9.10", "-m", "Release")
        self.run_command("git", "commit", "--allow-empty", "-qm", "New toolbar")
        changelog = self.update()
        self.assertIn("  * New toolbar", changelog)
        self.assertNotIn("  * Initial snapshot", changelog)

    def test_exact_release_tag_preserves_changelog(self):
        self.run_command("git", "tag", "-a", "v2.9.10", "-m", "Release")
        previous = (self.root / "debian/changelog").read_text()
        self.assertEqual(self.update(), previous)


if __name__ == "__main__":
    unittest.main()
