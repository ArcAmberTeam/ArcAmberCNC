#!/usr/bin/env python3
"""Offline release acceptance through the deployer's public CLI.

All filesystem effects are contained in TemporaryDirectory; HTTP uses a local
random port. No production helper, SSH, apt, or LinuxCNC is invoked.
"""
import fcntl
import functools
import gzip
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import unittest

HELPER = Path(__file__).with_name("web_release.py")
SHA_A = "a" * 40
SHA_B = "b" * 40


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class WebReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        (self.base / "releases").mkdir()
        (self.base / "incoming").mkdir()
        handler = functools.partial(QuietHandler, directory=str(self.base / "current"))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def bundle(self, sha=SHA_A, *, extra=(), metadata=None, index=b"<html>Web UI</html>", raw=None):
        release = f"42-1-{sha}"
        directory = self.base / "incoming" / release
        directory.mkdir(exist_ok=True)
        if raw is None:
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w") as archive:
                files = {
                    "index.html": index,
                    "build-info.json": json.dumps(metadata or {"commit": sha, "interface": "web"}).encode(),
                    "assets/app.js": b"document.title = 'Web';",
                }
                for name, data in files.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mode = 0o777
                    archive.addfile(info, io.BytesIO(data))
                for info, data in extra:
                    archive.addfile(info, io.BytesIO(data) if data is not None else None)
            raw = stream.getvalue()
        (directory / "web.tar.gz").write_bytes(gzip.compress(raw))
        (directory / "COMMIT").write_text(sha + "\n")
        self.manifest(directory)
        return release, directory

    def manifest(self, directory):
        (directory / "SHA256SUMS").write_text("".join(
            f"{hashlib.sha256((directory / name).read_bytes()).hexdigest()}  {name}\n"
            for name in ("web.tar.gz", "COMMIT")))

    def cli(self, *args, success=True):
        result = subprocess.run([sys.executable, "-I", str(HELPER), *map(str, args)],
                                capture_output=True, text=True, timeout=10)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def install(self, release, *, url=None, success=True):
        return self.cli("install", release, "--base", self.base,
                        "--health-url", url or self.url, "--health-timeout", "0.3", success=success)

    def test_valid_bundle_and_replacement_are_served(self):
        release, directory = self.bundle()
        self.cli("verify-bundle", directory, SHA_A)
        self.install(release)
        self.assertEqual((self.base / "current").readlink(), Path("releases") / release)
        self.assertEqual((self.base / "current/index.html").stat().st_mode & 0o777, 0o644)
        replacement, _ = self.bundle(SHA_B, index=b"<html>New Web UI</html>")
        self.install(replacement)
        self.assertEqual((self.base / "current/build-info.json").read_text(),
                         json.dumps({"commit": SHA_B, "interface": "web"}))
        self.assertTrue((self.base / "releases" / release).is_dir())

    def test_commit_mismatch_is_rejected_before_activation(self):
        release, directory = self.bundle()
        self.cli("verify-bundle", directory, SHA_B, success=False)
        (directory / "COMMIT").write_text(SHA_B + "\n")
        self.manifest(directory)
        self.install(release, success=False)
        self.assertFalse((self.base / "current").exists())

    def test_modified_archive_is_rejected(self):
        release, directory = self.bundle()
        with (directory / "web.tar.gz").open("ab") as target:
            target.write(b"tampered")
        self.install(release, success=False)
        self.assertFalse((self.base / "current").is_symlink())

    def test_manifest_cannot_redirect_verification(self):
        release, directory = self.bundle()
        manifest = directory / "SHA256SUMS"
        manifest.write_text(manifest.read_text().replace("web.tar.gz", "../outside"))
        self.install(release, success=False)
        self.assertFalse((self.base / "current").is_symlink())

    def test_bundle_rejects_symlink_and_extra_uploaded_script(self):
        release, directory = self.bundle()
        real_commit = self.base / "real-commit"
        (directory / "COMMIT").rename(real_commit)
        (directory / "COMMIT").symlink_to(real_commit)
        self.install(release, success=False)
        (directory / "COMMIT").unlink()
        real_commit.rename(directory / "COMMIT")
        (directory / "install.sh").write_text("touch /should-never-run")
        self.install(release, success=False)

    def test_archive_rejects_escaping_links_special_files_and_duplicate_paths(self):
        invalid = []
        for name in ("../escaped", "/escaped", "assets/../../escaped", "assets\\escaped"):
            info = tarfile.TarInfo(name)
            info.size = 1
            invalid.append((info, b"x"))
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE):
            info = tarfile.TarInfo("unsafe")
            info.type = kind
            info.linkname = "/tmp/escaped"
            invalid.append((info, None))
        info = tarfile.TarInfo("./index.html")
        info.size = 1
        invalid.append((info, b"x"))
        for item in invalid:
            with self.subTest(name=item[0].name, kind=item[0].type):
                release, _ = self.bundle(extra=[item])
                self.install(release, success=False)
                self.assertFalse((self.base / "current").is_symlink())
                self.assertEqual(list((self.base / "releases").iterdir()), [])

    def test_oversized_tar_entry_rejected_without_reading_body(self):
        info = tarfile.TarInfo("huge.bin")
        info.size = 65 * 1024 * 1024
        release, _ = self.bundle(raw=info.tobuf() + bytes(1024))
        result = self.install(release, success=False)
        self.assertIn("size limit", result.stderr)

    def test_build_commit_and_empty_index_rejected(self):
        release, _ = self.bundle(metadata={"commit": SHA_B})
        self.install(release, success=False)
        release, _ = self.bundle(index=b"")
        self.install(release, success=False)
        self.assertFalse((self.base / "current").is_symlink())

    def test_failed_http_verification_restores_previous_release(self):
        previous, _ = self.bundle()
        self.install(previous)
        release, _ = self.bundle(SHA_B)
        # The local server returns 404 for this endpoint, exercising rollback.
        self.install(release, url=self.url + "/unavailable", success=False)
        self.assertEqual((self.base / "current").readlink(), Path("releases") / previous)
        self.assertFalse((self.base / "releases" / release).exists())

    def test_first_failed_http_verification_removes_current(self):
        release, _ = self.bundle()
        self.install(release, url=self.url + "/unavailable", success=False)
        self.assertFalse((self.base / "current").is_symlink())
        self.assertEqual(list((self.base / "releases").iterdir()), [])

    def test_http_success_with_stale_files_is_rejected(self):
        previous, _ = self.bundle()
        self.install(previous)
        static_handler = functools.partial(QuietHandler, directory=str(self.base / "releases" / previous))
        stale_server = ThreadingHTTPServer(("127.0.0.1", 0), static_handler)
        thread = threading.Thread(target=stale_server.serve_forever, daemon=True)
        thread.start()
        try:
            release, _ = self.bundle(SHA_B)
            self.install(release, url=f"http://127.0.0.1:{stale_server.server_port}", success=False)
            self.assertEqual((self.base / "current").readlink(), Path("releases") / previous)
        finally:
            stale_server.shutdown()
            stale_server.server_close()

    def test_current_cannot_reference_an_unmanaged_directory(self):
        (self.base / "current").symlink_to(self.base / "incoming")
        release, _ = self.bundle()
        self.install(release, success=False)
        self.assertEqual((self.base / "current").readlink(), self.base / "incoming")

    def test_deployment_waits_for_the_single_writer_lock(self):
        release, _ = self.bundle()
        with (self.base / ".deploy.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            process = subprocess.Popen([
                sys.executable, "-I", str(HELPER), "install", release,
                "--base", str(self.base), "--health-url", self.url,
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                time.sleep(0.2)
                self.assertIsNone(process.poll())
                self.assertFalse((self.base / "current").is_symlink())
                fcntl.flock(lock, fcntl.LOCK_UN)
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, stderr + stdout)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

    def test_session_termination_rolls_back_the_current_pointer(self):
        previous, _ = self.bundle()
        self.install(previous)
        release, _ = self.bundle(SHA_B)
        process = subprocess.Popen([
            sys.executable, "-I", str(HELPER), "install", release,
            "--base", str(self.base), "--health-url", self.url + "/unavailable",
            "--health-timeout", "15",
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 3
            expected = Path("releases") / release
            while (self.base / "current").readlink() != expected and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual((self.base / "current").readlink(), expected)
            process.terminate()
            stdout, stderr = process.communicate(timeout=5)
            self.assertNotEqual(process.returncode, 0, stdout)
            self.assertIn("restored previous", stderr)
            self.assertEqual((self.base / "current").readlink(), Path("releases") / previous)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_release_id_and_existing_release_are_not_reused(self):
        release, _ = self.bundle()
        self.install("../escape", success=False)
        self.install(release)
        self.install(release, success=False)
        self.assertTrue((self.base / "current/index.html").is_file())


if __name__ == "__main__":
    unittest.main()
