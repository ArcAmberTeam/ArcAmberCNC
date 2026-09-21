#!/usr/bin/env python3
"""Package only Vite's static output; this CLI owns release filesystem writes."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile


def package(dist, output, commit):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("commit must be a full lowercase Git SHA")
    dist = dist.resolve()
    output = output.resolve()
    if output == dist or dist in output.parents:
        raise ValueError("release output must be outside the build directory")
    files = sorted(path for path in dist.rglob("*") if not path.is_dir())
    if not (dist / "index.html").is_file() or not (dist / "index.html").stat().st_size:
        raise ValueError("build has no non-empty index.html")
    # Also reject directory symlinks which rglob does not traverse.
    if any(path.is_symlink() for path in dist.rglob("*")):
        raise ValueError("static build must not contain symbolic links")
    for path in files:
        if not path.is_file() or path.relative_to(dist).as_posix() == "build-info.json":
            raise ValueError(f"unexpected build entry: {path.name}")
    output.mkdir(parents=True, exist_ok=False)
    metadata = (json.dumps({"commit": commit, "interface": "web"}, sort_keys=True) + "\n").encode()
    with tarfile.open(output / "web.tar.gz", "w:gz") as archive:
        for path in files:
            archive.add(path, arcname=path.relative_to(dist).as_posix(), recursive=False)
        entry = tarfile.TarInfo("build-info.json")
        entry.size = len(metadata)
        entry.mode = 0o644
        archive.addfile(entry, io.BytesIO(metadata))
    (output / "COMMIT").write_text(commit + "\n", encoding="ascii")
    checksums = "".join(
        f"{hashlib.sha256((output / name).read_bytes()).hexdigest()}  {name}\n"
        for name in ("COMMIT", "web.tar.gz")
    )
    (output / "SHA256SUMS").write_text(checksums, encoding="ascii")
    print(f"Packaged Web commit {commit}: {len(files)} static files in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    package(args.dist, args.output, args.commit)
