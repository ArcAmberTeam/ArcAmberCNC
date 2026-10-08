#!/usr/bin/env python3
"""List existing checkout files for native CI archives, preserving symlink seams."""

import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(sys.argv[1]).resolve()
    result = subprocess.run(
        ["git", "-c", f"safe.directory={root}", "-C", str(root), "ls-files",
         "--cached", "--others", "--exclude-standard", "-z", "--", ".",
         ":!:native-logs"],
        check=True, stdout=subprocess.PIPE,
    )
    for raw in sorted(set(result.stdout.split(b"\0")) - {b""}):
        relative = Path(os.fsdecode(raw))
        path = root / relative
        # Deleted tracked files and stale tracked descendants of a newly
        # introduced compatibility symlink must not re-enter the archive.
        if not (path.is_file() or path.is_symlink()):
            continue
        if any((root / parent).is_symlink() for parent in relative.parents):
            continue
        sys.stdout.buffer.write(raw + b"\0")


if __name__ == "__main__":
    main()
