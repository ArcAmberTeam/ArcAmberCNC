"""Continuous CAM2 jog through real TCP and the public Unix controller service."""

import asyncio
import json
import socket
import struct
import tempfile
import unittest
import uuid
from pathlib import Path

from betterlinuxcnc_service import serve as serve_control
from service_process import serve, wait_ready
from wire import encode_frame


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
        self.controllers = []

        def factory(**options):
            controller = FakeController(self.log, **options)
            self.controllers.append(controller)
            return controller

        self.stop_control = asyncio.Event()
        self.controller_task = asyncio.create_task(
            serve_control(
                self.control,
                controller_factory=factory,
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
        await wait_ready(self.server, self.port)
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

    async def local(self):
        reader, writer = await asyncio.open_unix_connection(str(self.control))
        self.clients.append((reader, writer))
        return reader, writer

    async def local_rpc(self, client, method, params):
        reader, writer = client
        body = json.dumps(
            {
                "version": 2,
                "request_id": uuid.uuid4().hex,
                "method": method,
                "params": params,
            }
        ).encode()
        writer.write(struct.pack("!I", len(body)) + body)
        await writer.drain()
        async with asyncio.timeout(3):
            size = struct.unpack("!I", await reader.readexactly(4))[0]
            return json.loads(await reader.readexactly(size))

    async def rpc(self, reader, writer, method, params):
        message = {
            "version": 2,
            "requestId": uuid.uuid4().hex,
            "method": method,
            "params": params,
        }
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
        command = {
            "jogId": str(uuid.uuid4()),
            "axis": "Y",
            "direction": 1,
            "feedRate": 300,
        }
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

    async def test_incomplete_tcp_frame_does_not_extend_the_jog_lease(self):
        reader, writer = await self.connect()
        _, reply = await self.start(reader, writer)
        self.assertTrue(reply["result"]["accepted"])
        writer.write(b"CAM2JOG_KEEPALIVE")
        await writer.drain()
        await asyncio.sleep(0.55)
        await self.wait_stopped()
        self.assertEqual(sum(action == "jog.start" for action, _ in self.log), 1)

    async def test_service_shutdown_revokes_jog_ownership(self):
        reader, writer = await self.connect()
        _, reply = await self.start(reader, writer)
        self.assertTrue(reply["result"]["accepted"])
        self.stop_cam.set()
        await self.server
        await self.wait_stopped()
        self.assertEqual(await reader.read(), b"")

    async def test_second_control_owner_is_rejected_and_invalid_parameters_never_dispatch(
        self,
    ):
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

    async def test_desktop_and_cam_share_one_controller_without_releasing_desktop(self):
        desktop = await self.local()
        self.assertTrue(
            (await self.local_rpc(desktop, "session.attach", {}))["result"]["connected"]
        )
        reader, writer = await self.connect()
        command, reply = await self.start(reader, writer, axis="X")
        self.assertTrue(reply["result"]["accepted"])
        self.assertEqual(len(self.controllers), 1)
        await self.rpc(reader, writer, "jog.stop", {"jogId": command["jogId"]})
        await self.wait_stopped()
        self.assertTrue(
            (await self.local_rpc(desktop, "session.status", {}))["result"]["connected"]
        )
        other = await self.local()
        self.assertEqual(
            (await self.local_rpc(other, "session.attach", {}))["error"]["code"],
            "control_in_use",
        )

    async def test_local_stop_overrides_cam_and_revokes_remote_renewal(self):
        desktop = await self.local()
        await self.local_rpc(desktop, "session.attach", {})
        reader, writer = await self.connect()
        command, reply = await self.start(reader, writer)
        self.assertTrue(reply["result"]["accepted"])
        reply = await self.local_rpc(
            desktop, "command.execute", {"action": "machine.estop", "payload": {}}
        )
        self.assertTrue(reply["result"]["accepted"])
        actions = [action for action, _ in self.log]
        self.assertLess(actions.index("stop"), actions.index("machine.estop"))
        reply = await self.rpc(reader, writer, "jog.keepalive", {"jogId": command["jogId"]})
        self.assertEqual(reply["error"]["code"], "jog_expired")

    async def test_cam_cannot_interrupt_existing_desktop_jog(self):
        desktop = await self.local()
        await self.local_rpc(desktop, "session.attach", {})
        await self.local_rpc(
            desktop,
            "command.execute",
            {"action": "jog.start", "payload": {"axis": "X", "velocity": 0.1}},
        )
        reader, writer = await self.connect()
        _, reply = await self.start(reader, writer)
        self.assertEqual(reply["error"]["code"], "control_in_use")
        self.assertFalse(any(action == "stop" for action, _ in self.log))

    async def test_desktop_heartbeat_cannot_renew_independent_cam_service_lease(self):
        desktop = await self.local()
        await self.local_rpc(desktop, "session.attach", {})
        remote = await self.local()
        command = {
            "jogId": str(uuid.uuid4()),
            "axis": "X",
            "direction": 1,
            "feedRate": 60,
        }
        reply = await self.local_rpc(remote, "cam.jog.start", command)
        self.assertTrue(reply["result"]["accepted"])
        for _ in range(7):
            await asyncio.sleep(0.12)
            await self.local_rpc(desktop, "session.status", {"jog_lease": True})
        await self.wait_stopped()
        reply = await self.local_rpc(remote, "cam.jog.keepalive", {"jogId": command["jogId"]})
        self.assertEqual(reply["error"]["code"], "jog_expired")
        self.assertEqual(sum(action == "jog.start" for action, _ in self.log), 1)


if __name__ == "__main__":
    unittest.main()
