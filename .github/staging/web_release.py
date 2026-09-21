#!/usr/bin/env python3
"""Static Web release boundary: validate bundles and atomically publish them.

The installed copy and its shell entry point are root-owned provisioning files.
Uploaded bundles contain data only. Tests use this same CLI with temporary paths
and a loopback HTTP server; no LinuxCNC, SSH, or package manager is involved.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request

SHA = re.compile(r"[0-9a-f]{40}\Z")
RELEASE = re.compile(r"[0-9]+-[0-9]+-[0-9a-f]{40}\Z")
MANIFEST_LINE = re.compile(r"([0-9a-f]{64}) [ *](COMMIT|web\.tar\.gz)\Z")
BUNDLE_LIMITS = {"COMMIT": 41, "SHA256SUMS": 256, "web.tar.gz": 64 * 1024 * 1024}
EXPANDED_LIMIT = 256 * 1024 * 1024
FILE_LIMIT = 64 * 1024 * 1024
MEMBER_LIMIT = 10000


def _read_bundle(directory: Path, destination: Path | None = None) -> dict[str, bytes | Path]:
    """Open untrusted incoming data relative to a no-follow directory descriptor."""
    result: dict[str, bytes | Path] = {}
    flags = os.O_RDONLY | os.O_NOFOLLOW
    with contextlib.ExitStack() as stack:
        directory_fd = os.open(directory, flags | os.O_DIRECTORY)
        stack.callback(os.close, directory_fd)
        if set(os.listdir(directory_fd)) != set(BUNDLE_LIMITS):
            raise ValueError("Bundle must contain only COMMIT, SHA256SUMS, and web.tar.gz")
        for name, limit in BUNDLE_LIMITS.items():
            fd = os.open(name, flags | os.O_NONBLOCK, dir_fd=directory_fd)
            with os.fdopen(fd, "rb") as source:
                info = os.fstat(source.fileno())
                if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= limit:
                    raise ValueError(f"Invalid bundle file type or size: {name}")
                data = source.read(limit + 1)
                if len(data) > limit:
                    raise ValueError(f"Bundle file exceeds limit: {name}")
            if destination is None:
                result[name] = data
            else:
                target = destination / name
                target.write_bytes(data)
                result[name] = target
    return result


def _bytes(value: bytes | Path) -> bytes:
    return value if isinstance(value, bytes) else value.read_bytes()


def _verify_bundle(bundle: dict[str, bytes | Path], expected: str) -> None:
    if not SHA.fullmatch(expected) or _bytes(bundle["COMMIT"]) != (expected + "\n").encode():
        raise ValueError("COMMIT must match the selected immutable commit")
    entries = {}
    for line in _bytes(bundle["SHA256SUMS"]).decode("ascii").splitlines():
        match = MANIFEST_LINE.fullmatch(line)
        if not match or match[2] in entries:
            raise ValueError("Invalid checksum manifest")
        entries[match[2]] = match[1]
    if set(entries) != {"COMMIT", "web.tar.gz"}:
        raise ValueError("Checksum manifest must cover exactly COMMIT and web.tar.gz")
    for name, digest in entries.items():
        if hashlib.sha256(_bytes(bundle[name])).hexdigest() != digest:
            raise ValueError(f"Checksum mismatch: {name}")


def _unpack(archive: Path, scratch: Path, output: Path, expected: str) -> None:
    # Bound decompression before parsing tar/PAX headers, which may be malicious.
    raw_tar = scratch / "payload.tar"
    total = 0
    with gzip.open(archive, "rb") as source, raw_tar.open("xb") as target:
        while block := source.read(1024 * 1024):
            total += len(block)
            if total > EXPANDED_LIMIT:
                raise ValueError("Expanded archive exceeds size limit")
            target.write(block)
    output.mkdir(mode=0o755)
    seen: set[str] = set()
    with tarfile.open(raw_tar, mode="r:") as archive_file:
        for number, member in enumerate(archive_file, 1):
            if number > MEMBER_LIMIT:
                raise ValueError("Archive has too many entries")
            path = PurePosixPath(member.name)
            if (path.is_absolute() or ".." in path.parts or "\\" in member.name
                    or "\x00" in member.name):
                raise ValueError(f"Unsafe archive path: {member.name!r}")
            normalized = str(path)
            if normalized in seen:
                raise ValueError(f"Duplicate archive path: {member.name!r}")
            seen.add(normalized)
            if not (member.isfile() or member.isdir()) or member.sparse is not None:
                raise ValueError(f"Unsupported archive entry: {member.name!r}")
            if any(key.startswith("GNU.sparse") for key in member.pax_headers):
                raise ValueError("Sparse archive entries are forbidden")
            if not 0 <= member.size <= FILE_LIMIT:
                raise ValueError(f"Archive entry exceeds size limit: {member.name!r}")
            if normalized == ".":
                if not member.isdir():
                    raise ValueError("Archive root must be a directory")
                continue
            target = output.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            if member.isdir():
                target.mkdir(exist_ok=True, mode=0o755)
                continue
            with archive_file.extractfile(member) as source, target.open("xb") as sink:
                shutil.copyfileobj(source, sink)
            target.chmod(0o644)
    index = output / "index.html"
    if not index.is_file() or index.stat().st_size == 0:
        raise ValueError("Archive must contain a nonempty root index.html")
    build_info = json.loads((output / "build-info.json").read_text())
    if not isinstance(build_info, dict) or build_info.get("commit") != expected:
        raise ValueError("build-info.json commit does not match COMMIT")


def _owned_directory(directory: Path) -> None:
    info = directory.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_mode & 0o022):
        raise ValueError(f"Deployment directory must be owned by installer and not writable by others: {directory}")


@contextlib.contextmanager
def _lock(base: Path):
    fd = os.open(base / ".deploy.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("Invalid deployment lock")
        deadline = time.monotonic() + 600
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Timed out waiting for deployment lock")
                time.sleep(0.1)
        yield


def _switch(base: Path, target: str | None) -> None:
    current = base / "current"
    if target is None:
        current.unlink(missing_ok=True)
        return
    temporary = base / ".current-next"
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target)
    os.replace(temporary, current)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Deployment health check must not redirect")


def _verify_http(url: str, destination: Path, expected: str, timeout: float) -> None:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    expected_index = hashlib.sha256((destination / "index.html").read_bytes()).digest()
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            received = {}
            for name in ("build-info.json", "index.html"):
                request = urllib.request.Request(
                    f"{url.rstrip('/')}/{name}?release={expected}",
                    headers={"Cache-Control": "no-cache"},
                )
                with opener.open(request, timeout=max(0.05, min(2, deadline - time.monotonic()))) as response:
                    if response.status != 200:
                        raise ValueError(f"HTTP health check returned {response.status}")
                    received[name] = response.read(FILE_LIMIT + 1)
                if len(received[name]) > FILE_LIMIT:
                    raise ValueError("HTTP health response exceeds limit")
            info = json.loads(received["build-info.json"])
            if not isinstance(info, dict) or info.get("commit") != expected:
                raise ValueError("Served build-info.json has a different commit")
            if hashlib.sha256(received["index.html"]).digest() != expected_index:
                raise ValueError("Served index.html does not match the release")
            return
        except (OSError, ValueError, urllib.error.URLError) as error:
            last_error = error
            time.sleep(min(0.2, max(0, deadline - time.monotonic())))
    raise RuntimeError(f"HTTP verification failed: {last_error}")


def _install(base: Path, release: str, health_url: str, health_timeout: float) -> None:
    if not RELEASE.fullmatch(release):
        raise ValueError("Release must be run-id, attempt, and 40-character commit")
    _owned_directory(base)
    releases = base / "releases"
    _owned_directory(releases)
    with _lock(base):
        destination = releases / release
        if destination.exists() or destination.is_symlink():
            raise ValueError("Release already exists")
        current = base / "current"
        previous = None
        if current.is_symlink():
            previous = os.readlink(current)
            prior_path = current.resolve(strict=True)
            if prior_path.parent != releases.resolve() or not prior_path.is_dir():
                raise ValueError("Current release points outside releases directory")
        elif current.exists():
            raise ValueError("Current must be an installer-owned symlink")
        expected = release.rsplit("-", 1)[1]
        with tempfile.TemporaryDirectory(prefix=".prepare-", dir=releases) as scratch_name:
            scratch = Path(scratch_name)
            bundle = _read_bundle(base / "incoming" / release, scratch)
            _verify_bundle(bundle, expected)
            payload = scratch / "public"
            _unpack(scratch / "web.tar.gz", scratch, payload, expected)
            os.replace(payload, destination)
        try:
            _switch(base, f"releases/{release}")
            _verify_http(health_url, destination, expected, health_timeout)
        except BaseException:
            _switch(base, previous)
            shutil.rmtree(destination)
            print("Web deployment failed; restored previous current pointer" if previous
                  else "First Web deployment failed; current pointer removed", file=sys.stderr)
            raise
        print(f"Accepted Web commit {expected}; local HTTP index and build-info verified")


def _interrupted(signum, _frame):
    raise RuntimeError(f"Deployment interrupted by signal {signum}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify-bundle")
    verify.add_argument("directory", type=Path)
    verify.add_argument("commit")
    install = commands.add_parser("install")
    install.add_argument("release")
    install.add_argument("--base", type=Path, required=True)
    install.add_argument("--health-url", required=True)
    install.add_argument("--health-timeout", type=float, default=15)
    args = parser.parse_args()
    try:
        if args.command == "verify-bundle":
            _verify_bundle(_read_bundle(args.directory), args.commit)
        else:
            if not 0 < args.health_timeout <= 60:
                raise ValueError("Health timeout must be between 0 and 60 seconds")
            # SSH/session termination must take the same rollback path as a failed probe.
            for termination_signal in (signal.SIGTERM, signal.SIGHUP):
                signal.signal(termination_signal, _interrupted)
            _install(args.base, args.release, args.health_url, args.health_timeout)
    except (OSError, ValueError, RuntimeError, tarfile.TarError, EOFError) as error:
        print(f"Web release rejected: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
