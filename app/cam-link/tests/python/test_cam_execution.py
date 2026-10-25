"""Received machining jobs through public Controller and real network/service seams."""

import asyncio
import base64
import hashlib
import json
import socket
import struct
import tempfile
import unittest
import uuid
from pathlib import Path

from bettercnc_controller import Controller
from betterlinuxcnc_service import serve as serve_control
from service_process import serve as serve_cam
from service_process import wait_ready
from test_controller import FakeLinuxCNC
from wire import encode_frame


class CamExecutionNetworkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/tmp", prefix="cam-run-")
        self.root = Path(self.temp.name)
        self.inbox = self.root / "inbox"
        self.inbox.mkdir(mode=0o700)
        self.module = FakeLinuxCNC()
        self.control = self.root / "ctl" / "control.sock"
        self.control_stop, self.cam_stop = asyncio.Event(), asyncio.Event()
        self.factory_calls = 0
        self.controllers = []

        def factory(**kwargs):
            self.factory_calls += 1
            controller = Controller(module=self.module, **kwargs)
            self.controllers.append(controller)
            return controller

        self.control_task = asyncio.create_task(
            serve_control(
                self.control,
                ini_path="/machine/machine.ini",
                cam_inbox=self.inbox,
                controller_factory=factory,
                stop_event=self.control_stop,
            )
        )
        for _ in range(100):
            if self.control.exists():
                break
            await asyncio.sleep(0.01)
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.setblocking(False)
        self.port = listener.getsockname()[1]
        self.cam_task = asyncio.create_task(
            serve_cam(
                self.inbox,
                token="t" * 32,
                control_socket=self.control,
                sock=listener,
                auto_run=True,
                stop_event=self.cam_stop,
            )
        )
        self.connections = []
        self.serial = 0
        await wait_ready(self.cam_task, self.port)

    async def asyncTearDown(self):
        for _, writer in self.connections:
            writer.close()
        self.cam_stop.set()
        self.control_stop.set()
        await asyncio.wait_for(asyncio.gather(self.cam_task, self.control_task), 5)
        self.temp.cleanup()

    async def connect(self):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        self.connections.append((reader, writer))
        self.assertTrue(
            (await self.rpc((reader, writer), "session.auth", {"token": "t" * 32}))["result"][
                "authenticated"
            ]
        )
        return reader, writer

    async def rpc(self, connection, method, params):
        self.serial += 1
        reader, writer = connection
        writer.write(
            encode_frame(
                {
                    "version": 2,
                    "requestId": str(self.serial),
                    "method": method,
                    "params": params,
                }
            )
        )
        await writer.drain()
        async with asyncio.timeout(4):
            header = await reader.readexactly(24)
            body = await reader.readexactly(struct.unpack("!I", header[20:24])[0])
            return json.loads(body)

    async def upload(self, connection, transfer):
        body = b"G21\nG90\nM2\n"
        reply = await self.rpc(
            connection,
            "upload.begin",
            {
                "transferId": transfer,
                "filename": "part.nc",
                "size": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            },
        )
        self.assertIn("result", reply)
        await self.rpc(
            connection,
            "upload.chunk",
            {"offset": 0, "data": base64.b64encode(body).decode()},
        )
        return await self.rpc(connection, "upload.finish", {})

    async def test_new_upload_runs_after_client_disconnect_and_receipt_retry_never_restarts(
        self,
    ):
        connection = await self.connect()
        transfer = str(uuid.uuid4())
        result = await self.upload(connection, transfer)
        self.assertEqual(result["result"]["job"]["state"], "loading")
        connection[1].close()
        await connection[1].wait_closed()
        for _ in range(40):
            if self.module.calls:
                self.module.confirm(
                    state=self.module.RCS_EXEC if self.module.calls[-1][0] == "auto" else None
                )
            if self.module.calls and self.module.calls[-1][0] == "auto":
                break
            await asyncio.sleep(0.1)
        self.assertEqual(self.module.calls[-1][0], "auto")
        next_connection = await self.connect()
        receipt = await self.rpc(next_connection, "upload.receipt", {"transferId": transfer})
        self.assertEqual(receipt["result"]["transferId"], transfer)
        before = sum(method == "auto" for method, _ in self.module.calls)
        await self.rpc(next_connection, "job.start", {"transferId": transfer})
        await asyncio.sleep(0.15)
        self.assertEqual(sum(method == "auto" for method, _ in self.module.calls), before)
        self.assertEqual(self.factory_calls, 1)

    async def test_desktop_disconnect_preserves_service_job_and_existing_single_writer(
        self,
    ):
        reader, writer = await asyncio.open_unix_connection(str(self.control))
        request = json.dumps(
            {
                "version": 2,
                "request_id": "attach",
                "method": "session.attach",
                "params": {},
            }
        ).encode()
        writer.write(struct.pack("!I", len(request)) + request)
        await writer.drain()
        size = struct.unpack("!I", await reader.readexactly(4))[0]
        self.assertIn("result", json.loads(await reader.readexactly(size)))
        connection = await self.connect()
        transfer = str(uuid.uuid4())
        await self.upload(connection, transfer)
        writer.close()
        await writer.wait_closed()
        for _ in range(30):
            if self.module.calls:
                self.module.confirm(
                    state=self.module.RCS_EXEC if self.module.calls[-1][0] == "auto" else None
                )
            if self.module.calls and self.module.calls[-1][0] == "auto":
                break
            await asyncio.sleep(0.1)
        self.assertEqual(self.module.calls[-1][0], "auto")
        self.assertEqual(self.factory_calls, 1)

    async def test_offline_rejection_is_reported_in_receipt_without_program_open(self):
        self.module.available = False
        connection = await self.connect()
        result = await self.upload(connection, str(uuid.uuid4()))
        self.assertEqual(result["result"]["state"], "received")
        self.assertEqual(result["result"]["job"]["state"], "error")
        self.assertIn("未连接", result["result"]["job"]["message"])
        self.assertEqual(self.module.calls, [])
