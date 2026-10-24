"""Continuous CAM2 jog through real TCP and the public Unix controller service."""

import asyncio
import json
import socket
import struct
import tempfile
import unittest
import uuid
from pathlib import Path

from bettercnc_cam_link import serve
from bettercnc_cam_link.protocol import encode_frame
from betterlinuxcnc_service import serve as serve_control


class FakeController:
    def __init__(self, log, **_options):
        self.log = log
        self.snapshot = {"connected": True, "motionMode": "world", "linearUnits": 0.1}

    def poll(self):
        return self.snapshot

    def dispatch(self, action, payload):
        self.log.append((action, payload))
        return True

    def stop_jog(self):
        self.log.append(("stop", {}))

    def close(self):
        self.stop_jog()


class CamJogTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/tmp", prefix="cam-jog-")
        self.root = Path(self.temp.name)
        self.control = self.root / "control" / "service.sock"
        self.log = []
        self.stop_control = asyncio.Event()
        self.controller_task = asyncio.create_task(
            serve_control(
                self.control,
                controller_factory=lambda **options: FakeController(self.log, **options),
                stop_event=self.stop_control,
            )
        )
        for _ in range(100):
            if self.control.exists():
                break
            await asyncio.sleep(0.01)
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen()
        self.sock.setblocking(False)
        self.port = self.sock.getsockname()[1]
        self.stop_cam = asyncio.Event()
        self.server = asyncio.create_task(
            serve(
                self.root / "inbox",
                token="t" * 32,
                control_socket=self.control,
                sock=self.sock,
                stop_event=self.stop_cam,
            )
        )
        await asyncio.sleep(0.03)
        self.clients = []

    async def asyncTearDown(self):
        for _reader, writer in self.clients:
            writer.close()
            await writer.wait_closed()
        self.stop_cam.set()
        await self.server
        self.stop_control.set()
        await self.controller_task
        self.temp.cleanup()

    async def connect(self):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        self.clients.append((reader, writer))
        self.assertTrue(
            (await self.rpc(reader, writer, "session.auth", {"token": "t" * 32}))["result"][
                "authenticated"
            ]
        )
        return reader, writer

    async def rpc(self, reader, writer, method, params):
        message = {"version": 2, "requestId": uuid.uuid4().hex, "method": method, "params": params}
        data = encode_frame(message)
        if method.startswith("jog."):
            self.assertEqual(
                data[4:20].rstrip(b"\x00"),
                {
                    "jog.start": b"JOG_START",
                    "jog.keepalive": b"JOG_KEEPALIVE",
                    "jog.stop": b"JOG_STOP",
                }[method],
            )
        writer.write(data)
        await writer.drain()
        async with asyncio.timeout(3):
            header = await reader.readexactly(24)
            return json.loads(await reader.readexactly(struct.unpack("!I", header[20:])[0]))

    async def start(self, reader, writer, **changes):
        command = {"jogId": str(uuid.uuid4()), "axis": "Y", "direction": 1, "feedRate": 300}
        command.update(changes)
        return command, await self.rpc(reader, writer, "jog.start", command)

    async def wait_stopped(self):
        for _ in range(100):
            if any(action == "stop" for action, _ in self.log):
                return
            await asyncio.sleep(0.01)
        self.fail("owned controller session did not stop")

    async def test_hold_renews_then_release_stops_and_does_not_replay(self):
        reader, writer = await self.connect()
        command, reply = await self.start(reader, writer)
        self.assertTrue(reply["result"]["accepted"])
        self.assertEqual(
            self.log[0],
            (
                "jog.start",
                {
                    "axis": "Y",
                    "mode": "world",
                    "direction": 1,
                    "velocity": 0.5,
                    "increment": 0,
                },
            ),
        )
        for _ in range(5):
            await asyncio.sleep(0.12)
            reply = await self.rpc(reader, writer, "jog.keepalive", {"jogId": command["jogId"]})
            self.assertTrue(reply["result"]["accepted"])
        self.assertFalse(any(action == "stop" for action, _ in self.log))
        await self.rpc(reader, writer, "jog.stop", {"jogId": command["jogId"]})
        await self.wait_stopped()
        reply = await self.rpc(reader, writer, "jog.start", command)
        self.assertEqual(reply["error"]["code"], "jog_busy")
        self.assertEqual(sum(action == "jog.start" for action, _ in self.log), 1)

    async def test_missing_heartbeat_expires_and_late_renewal_cannot_restart(self):
        reader, writer = await self.connect()
        command, reply = await self.start(reader, writer)
        self.assertTrue(reply["result"]["accepted"])
        await asyncio.sleep(0.55)
        await self.wait_stopped()
        reply = await self.rpc(reader, writer, "jog.keepalive", {"jogId": command["jogId"]})
        self.assertEqual(reply["error"]["code"], "jog_expired")
        self.assertEqual(sum(action == "jog.start" for action, _ in self.log), 1)

    async def test_tcp_disconnect_stops_owned_movement(self):
        reader, writer = await self.connect()
        _, reply = await self.start(reader, writer, axis="Z", direction=-1)
        self.assertTrue(reply["result"]["accepted"])
        writer.close()
        await writer.wait_closed()
        await self.wait_stopped()

    async def test_second_control_owner_is_rejected_and_invalid_parameters_never_dispatch(self):
        first_reader, first_writer = await self.connect()
        _, reply = await self.start(first_reader, first_writer)
        self.assertTrue(reply["result"]["accepted"])
        reader, writer = await self.connect()
        _, reply = await self.start(reader, writer)
        self.assertEqual(reply["error"]["code"], "control_in_use")
        _, reply = await self.start(reader, writer, direction=True)
        self.assertEqual(reply["error"]["code"], "invalid_params")
        _, reply = await self.start(reader, writer, feedRate=-1)
        self.assertEqual(reply["error"]["code"], "invalid_params")
        self.assertEqual(sum(action == "jog.start" for action, _ in self.log), 1)


if __name__ == "__main__":
    unittest.main()
