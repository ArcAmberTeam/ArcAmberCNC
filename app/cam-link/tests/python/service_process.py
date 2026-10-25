"""Launch the compiled Rust CLI for public cross-process contract tests."""

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path

_READY = set()


def binary():
    return os.environ["CAM_LINK_BINARY"]


@dataclass(frozen=True)
class DiscoveryOptions:
    device_id: str
    device_name: str = "LinuxCNC"
    address: str = "255.255.255.255"
    port: int = 8421
    bind_port: int | None = None
    interval: float = 3.0


async def wait_ready(task, port):
    async with asyncio.timeout(10):
        while port not in _READY:
            if task.done():
                await task
                raise AssertionError("service stopped before readiness")
            await asyncio.sleep(0.005)


async def serve(inbox, *, control_socket, sock, stop_event, token=None, discovery=None, **options):
    host, port = sock.getsockname()[:2]
    sock.close()
    command = [
        binary(),
        "--inbox",
        str(inbox),
        "--control-socket",
        str(control_socket),
        "--host",
        host,
        "--port",
        str(port),
    ]
    if token is not None:
        token_file = Path(inbox).parent / f"token-{port}"
        token_file.write_text(token)
        token_file.chmod(0o600)
        command += ["--token-file", str(token_file)]
    for key, value in options.items():
        if isinstance(value, bool):
            if value:
                command.append("--" + key.replace("_", "-"))
        else:
            command += ["--" + key.replace("_", "-"), str(value)]
    if discovery:
        command.append("--discover")
        for key, value in vars(discovery).items():
            if value is not None:
                command += [
                    "--"
                    + (key if key.startswith("device_") else "discovery_" + key).replace("_", "-"),
                    str(value),
                ]
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        line = await asyncio.wait_for(process.stdout.readline(), 10)
        if not line:
            error = (await process.stderr.read()).decode()
            raise OSError(error)
        assert json.loads(line)["port"] == port
        _READY.add(port)
        stopped = asyncio.create_task(stop_event.wait())
        exited = asyncio.create_task(process.wait())
        try:
            await asyncio.wait((stopped, exited), return_when=asyncio.FIRST_COMPLETED)
            if process.returncode is None:
                process.terminate()
            await asyncio.wait_for(exited, 5)
            assert process.returncode == 0, (await process.stderr.read()).decode()
        finally:
            stopped.cancel()
            exited.cancel()
            await asyncio.gather(stopped, exited, return_exceptions=True)
    finally:
        _READY.discard(port)
        if process.returncode is None:
            process.kill()
            await process.wait()
