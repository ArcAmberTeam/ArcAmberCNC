"""Exercise the real CAM backend HTTP API against Rust CAM2 and an injected controller.

Provide the two compiled binaries; PYTHONPATH must include app/controller/src and
app/controller/tests. No LinuxCNC core, simulator or hardware is started.
"""

import argparse
import asyncio
import json
import os
import socket
import sys
import tempfile
import urllib.request
import uuid
from pathlib import Path

from bettercnc_controller import Controller, StatusReader
from betterlinuxcnc_service import serve
from test_controller import FakeLinuxCNC


async def main(backend_binary, cam_link_binary):
    processes = []
    with tempfile.TemporaryDirectory(prefix="cam-roundtrip-", dir="/tmp") as temporary:
        root = Path(temporary)
        inbox = root / "inbox"
        inbox.mkdir(mode=0o700)
        ctl = root / "control" / "service.sock"
        stop = asyncio.Event()
        vendor = FakeLinuxCNC()
        vendor.status.motion_mode = vendor.TRAJ_MODE_TELEOP
        service = asyncio.create_task(
            serve(
                ctl,
                ini_path="/machine/machine.ini",
                cam_inbox=inbox,
                controller_factory=lambda **kw: Controller(module=vendor, **kw),
                status_reader_factory=lambda **kw: StatusReader(module=vendor, **kw),
                stop_event=stop,
            )
        )

        async def confirm():
            while not stop.is_set():
                if vendor.calls:
                    vendor.confirm(state=vendor.RCS_EXEC if vendor.calls[-1][0] == "auto" else None)
                await asyncio.sleep(0.02)

        ticker = asyncio.create_task(confirm())
        try:
            while not ctl.exists():
                await asyncio.sleep(0.01)
            listener = socket.socket()
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
            listener.close()
            backend = await asyncio.create_subprocess_exec(
                backend_binary,
                env=dict(os.environ, ARCAMBER_BACKEND_ADDR=f"127.0.0.1:{port}"),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            processes.append(backend)
            async with asyncio.timeout(20):
                while True:
                    if backend.returncode is not None:
                        raise AssertionError((await backend.stderr.read()).decode())
                    try:
                        reader, writer = await asyncio.open_connection("127.0.0.1", port)
                        writer.close()
                        await writer.wait_closed()
                        break
                    except ConnectionRefusedError:
                        await asyncio.sleep(0.05)
            device = str(uuid.uuid4())
            link = await asyncio.create_subprocess_exec(
                cam_link_binary,
                "--inbox",
                str(inbox),
                "--control-socket",
                str(ctl),
                "--port",
                "0",
                "--auto-run",
                "--discover",
                "--device-id",
                device,
                "--device-name",
                "Rust integration fixture",
                "--discovery-address",
                "127.0.0.1",
                "--discovery-port",
                "8421",
                "--discovery-bind-port",
                "0",
                "--discovery-interval",
                "0.1",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            processes.append(link)
            line = await asyncio.wait_for(link.stdout.readline(), 5)
            assert json.loads(line)["port"] > 0

            async def rpc(method, path, body=None):
                def send():
                    request = urllib.request.Request(
                        f"http://127.0.0.1:{port}/api/v1" + path,
                        data=None if body is None else json.dumps(body).encode(),
                        method=method,
                        headers={"Content-Type": "application/json", "X-ArcAmber-Client": "cam"},
                    )
                    with urllib.request.urlopen(request, timeout=15) as response:
                        return json.load(response)

                return await asyncio.to_thread(send)

            devices = await rpc("POST", "/machines/discover", {})
            assert any(d["deviceId"] == device for d in devices), devices
            paired = await rpc("POST", f"/machines/{device}/pair", {})
            assert paired["paired"], paired
            status = await rpc("GET", f"/machines/{device}/status")
            assert status["connected"], status
            jog = str(uuid.uuid4())
            accepted = await rpc(
                "POST",
                f"/machines/{device}/jog",
                {"jogId": jog, "axis": "X", "direction": 1, "feedRate": 60},
            )
            assert accepted["accepted"], accepted
            for _ in range(3):
                await asyncio.sleep(0.12)
                await rpc("POST", f"/machines/{device}/jog/{jog}", {})
            await rpc("DELETE", f"/machines/{device}/jog/{jog}")
            await asyncio.sleep(0.3)
            assert any(
                name == "jog" and args[0] == vendor.JOG_CONTINUOUS for name, args in vendor.calls
            ), vendor.calls
            assert any(
                name == "jog" and args[0] == vendor.JOG_STOP for name, args in vendor.calls
            ), vendor.calls
            transfer = str(uuid.uuid4())
            program = {"transferId": transfer, "filename": "fixture.nc", "gcode": "G21\nG90\nM2\n"}
            receipt = await rpc("POST", f"/machines/{device}/programs", program)
            assert receipt["state"] == "received" and receipt["job"]["state"] in (
                "loading",
                "starting",
                "running",
            ), receipt

            async def wait_job(state):
                async with asyncio.timeout(5):
                    while True:
                        current = await rpc("POST", f"/machines/{device}/programs", program)
                        if current["job"]["state"] == state:
                            return current
                        assert current["job"]["state"] in (
                            "loading",
                            "starting",
                            "running",
                        ), current
                        await asyncio.sleep(0.05)

            # Observe the controller's confirmed state before simulating completion.
            # Merely seeing auto() does not mean its native receipt was processed.
            await wait_job("running")
            before = sum(name == "auto" for name, args in vendor.calls)
            assert before == 1, vendor.calls
            await rpc("POST", f"/machines/{device}/programs", program)
            assert sum(name == "auto" for name, args in vendor.calls) == before
            ticker.cancel()
            await asyncio.gather(ticker, return_exceptions=True)
            vendor.status.interp_state = vendor.INTERP_IDLE
            vendor.status.state = vendor.RCS_DONE
            vendor.status.inpos = True
            vendor.status.queue = vendor.status.active_queue = 0
            await wait_job("completed")
            assert sum(name == "auto" for name, args in vendor.calls) == before
            print(
                json.dumps(
                    {
                        "discovery": True,
                        "oneClickPair": True,
                        "status": True,
                        "jogStartKeepaliveStop": True,
                        "uploadAutoRun": True,
                        "receiptRetryNoReplay": True,
                        "completed": True,
                        "hardware": "injected vendor only",
                    },
                    ensure_ascii=False,
                )
            )
        finally:
            stop.set()
            ticker.cancel()
            await asyncio.gather(ticker, return_exceptions=True)
            for process in reversed(processes):
                if process.returncode is None:
                    process.terminate()
                await asyncio.wait_for(process.wait(), 5)
                errors = await process.stderr.read()
                if errors:
                    print(errors.decode(), file=sys.stderr)
            await service


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", required=True, type=Path)
    parser.add_argument("--cam-link", required=True, type=Path)
    arguments = parser.parse_args()
    asyncio.run(main(str(arguments.backend.resolve()), str(arguments.cam_link.resolve())))
