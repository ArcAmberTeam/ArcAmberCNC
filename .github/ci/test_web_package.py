"""Test the public release-packaging CLI, not private implementation helpers."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest


class WebPackageTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.dist = self.root / "dist"
        self.dist.mkdir()
        (self.dist / "index.html").write_text("<html>Web UI</html>")
        (self.dist / "assets").mkdir()
        (self.dist / "assets/app.js").write_text("export const version = 1;")
        self.output = self.root / "release"

    def run_package(self, commit="a" * 40):
        return subprocess.run([
            sys.executable, str(Path(__file__).with_name("package-web.py")),
            "--dist", str(self.dist), "--output", str(self.output), "--commit", commit,
        ], capture_output=True, text=True, timeout=10)

    def test_release_contains_only_static_build_and_matching_commit(self):
        result = self.run_package()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.output / "COMMIT").read_text(), "a" * 40 + "\n")
        for line in (self.output / "SHA256SUMS").read_text().splitlines():
            digest, name = line.split("  ")
            self.assertEqual(hashlib.sha256((self.output / name).read_bytes()).hexdigest(), digest)
        with tarfile.open(self.output / "web.tar.gz") as archive:
            self.assertEqual(set(archive.getnames()), {"index.html", "assets/app.js", "build-info.json"})
            self.assertEqual(json.load(archive.extractfile("build-info.json"))["commit"], "a" * 40)

    def test_rejects_invalid_commit_without_creating_artifact(self):
        self.assertNotEqual(self.run_package("main").returncode, 0)
        self.assertFalse(self.output.exists())

    def test_rejects_symlinks_outside_build(self):
        (self.dist / "escape").symlink_to(self.root)
        self.assertNotEqual(self.run_package().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_rejects_stale_release_metadata(self):
        (self.dist / "build-info.json").write_text('{"commit":"stale"}')
        self.assertNotEqual(self.run_package().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_never_overwrites_an_existing_artifact(self):
        self.assertEqual(self.run_package().returncode, 0)
        before = (self.output / "web.tar.gz").read_bytes()
        self.assertNotEqual(self.run_package("b" * 40).returncode, 0)
        self.assertEqual((self.output / "web.tar.gz").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
