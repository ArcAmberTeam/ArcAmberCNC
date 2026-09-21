"""Local bounded request/reply transport. No LinuxCNC imports or hardware access."""

import argparse
import asyncio
import contextlib
import os
import signal
import socket
import stat
import struct
import tempfile
from pathlib import Path

from ._protocol import MAX_FRAME_BYTES, response

IO_TIMEOUT = 2.0
MAX_CLIENTS = 8


def default_socket() -> Path:
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir())
    return runtime / "betterlinuxcnc" / "control.sock"


async def serve(path: Path) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory = path.parent.lstat()
    if (
        not stat.S_ISDIR(directory.st_mode)
        or directory.st_uid != os.getuid()
        or stat.S_IMODE(directory.st_mode) & 0o077
    ):
        raise ValueError("socket directory must be owned by this user with mode 0700")

    clients: set[asyncio.Task] = set()

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        assert task is not None
        if len(clients) >= MAX_CLIENTS:
            writer.close()
            await writer.wait_closed()
            return
        clients.add(task)
        try:
            while True:
                async with asyncio.timeout(IO_TIMEOUT):
                    header = await reader.readexactly(4)
                    size = struct.unpack("!I", header)[0]
                    if not 0 < size <= MAX_FRAME_BYTES:
                        return
                    payload = await reader.readexactly(size)
                    reply = response(payload)
                    writer.write(struct.pack("!I", len(reply)) + reply)
                    await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError, TimeoutError):
            pass
        finally:
            clients.discard(task)
            writer.close()
            with contextlib.suppress(ConnectionError):
                await writer.wait_closed()

    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stopped.set)

    # Bind ourselves: asyncio's path-based helper may unlink an existing socket.
    # Never replace another process's endpoint, including on a second startup.
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    identity = None
    try:
        listener.bind(str(path))
        identity = path.lstat()
        path.chmod(0o600)
        listener.setblocking(False)
        server = await asyncio.start_unix_server(handle, sock=listener, limit=MAX_FRAME_BYTES)
        async with server:
            print(f"Local diagnostics service ready: {path}", flush=True)
            await stopped.wait()
    finally:
        listener.close()
        pending = list(clients)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        if identity is not None:
            with contextlib.suppress(FileNotFoundError):
                current = path.lstat()
                if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                    path.unlink()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(sig)


def main() -> None:
    parser = argparse.ArgumentParser(description="BetterLinuxCNC local diagnostics service")
    parser.add_argument("--socket", type=Path, default=default_socket())
    args = parser.parse_args()
    try:
        asyncio.run(serve(args.socket.absolute()))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Cannot start local service: {exc}\n")
