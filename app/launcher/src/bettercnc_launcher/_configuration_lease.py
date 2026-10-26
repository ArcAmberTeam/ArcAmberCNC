"""Exclude fixed privileged configuration saves for the managed launcher's lifetime."""

import contextlib
import fcntl
import os
import stat
from pathlib import Path


@contextlib.contextmanager
def configuration_lease(config, ini):
    managed = Path("/etc/betterlinuxcnc")
    paths = [config]
    if ini:
        paths.append(Path(ini).expanduser().absolute())
    if not any(path == managed or managed in path.parents for path in paths):
        yield
        return
    descriptor = os.open(
        "/var/lib/betterlinuxcnc/configuration.lock",
        os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != 0
            or info.st_mode & 0o022
            or info.st_nlink != 1
        ):
            raise ValueError("Untrusted configuration lease")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Configuration save in progress; retry startup later") from None
        yield
    finally:
        os.close(descriptor)
