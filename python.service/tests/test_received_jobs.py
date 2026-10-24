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

from test_controller import FakeClock, FakeLinuxCNC

from bettercnc_cam_link import serve as serve_cam
from bettercnc_cam_link.protocol import encode_frame
from bettercnc_cam_link.receiver import ProgramInbox
from bettercnc_controller import Controller
from betterlinuxcnc_service import serve as serve_control


def received(inbox, body=b"G21\nG90\nM2\n"):
    transfer_id = str(uuid.uuid4())
    upload = ProgramInbox(inbox).begin(
        transfer_id=transfer_id,
        filename="part.nc",
        size=len(body),
        sha256=hashlib.sha256(body).hexdigest(),
    )
    upload.write(0, body)
    upload.finish()
    return transfer_id


class ReceivedJobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/tmp", prefix="received-")
        self.addCleanup(self.temp.cleanup)
        self.inbox = Path(self.temp.name) / "inbox"
        self.transfer = received(self.inbox)
        self.module = FakeLinuxCNC()
        self.clock = FakeClock()
        self.controller = Controller(
            ini_path="/machine/machine.ini",
            module=self.module,
            clock=self.clock,
            cam_inbox=self.inbox,
        )
        self.addCleanup(self.controller.close)

    def running(self):
        self.controller.start_received(self.transfer)
        for _ in range(3):
            self.module.confirm(
                state=self.module.RCS_EXEC if self.module.calls[-1][0] == "auto" else None
            )
            self.controller.poll()
        self.assertEqual(self.module.calls[-1], ("auto", (self.module.AUTO_RUN, 0)))
        self.assertEqual(self.controller.received_status(self.transfer)["state"], "running")

    def finish(self):
        s = self.module.status
        s.interp_state = self.module.INTERP_IDLE
        s.state = self.module.RCS_DONE
        s.inpos = True
        s.queue = s.active_queue = 0
        self.controller.poll()

    def test_verified_file_loads_then_runs_and_completes_only_after_motion_done(self):
        self.running()
        s = self.module.status
        s.interp_state = self.module.INTERP_IDLE
        s.state = self.module.RCS_DONE
        s.inpos = False
        s.queue = 1
        self.controller.poll()
        self.assertEqual(self.controller.received_status(self.transfer)["state"], "running")
        self.finish()
        self.assertEqual(self.controller.received_status(self.transfer)["state"], "completed")
        calls = list(self.module.calls)
        self.controller.start_received(self.transfer)
        self.assertEqual(calls, self.module.calls)
        self.assertFalse(any(name == "mdi" for name, _ in calls))

    def test_received_content_is_snapshotted_before_load(self):
        record = self.controller.start_received(self.transfer)
        original = self.inbox / self.transfer / "part.nc"
        original.write_text("M2\n")
        self.assertEqual(Path(record["path"]).read_text(), "G21\nG90\nM2\n")
        self.assertEqual(self.module.calls[0], ("program_open", (record["path"],)))

    def test_offline_unhomed_estop_disabled_and_limit_override_never_issue_commands(self):
        for change in ("offline", "unhomed", "estop", "off", "limit"):
            with self.subTest(change=change):
                module = FakeLinuxCNC()
                if change == "offline":
                    module.available = False
                if change == "unhomed":
                    module.status.homed[0] = 0
                    module.ini_values[("TRAJ", "NO_FORCE_HOMING")] = "1"
                if change == "estop":
                    module.status.estop = True
                if change == "off":
                    module.status.enabled = False
                if change == "limit":
                    module.status.joint[0]["override_limits"] = True
                controller = Controller(
                    ini_path="/machine/machine.ini", module=module, cam_inbox=self.inbox
                )
                transfer = received(self.inbox)
                self.assertEqual(controller.start_received(transfer)["state"], "error")
                self.assertEqual(module.calls, [])
                controller.close()

    def test_corrupt_file_and_symlink_are_rejected_without_motion(self):
        (self.inbox / self.transfer / "part.nc").write_text("G0 X999\n")
        with self.assertRaises(ValueError):
            self.controller.start_received(self.transfer)
        self.assertEqual(self.module.calls, [])
        self.assertEqual(self.controller.received_status(self.transfer)["state"], "error")
        transfer = received(self.inbox)
        source = self.inbox / transfer / "part.nc"
        source.unlink()
        source.symlink_to(self.inbox / self.transfer / "part.nc")
        with self.assertRaises(ValueError):
            self.controller.start_received(transfer)
        self.assertEqual(self.module.calls, [])

    def test_restart_never_replays_an_incomplete_or_completed_job(self):
        self.running()
        other_module = FakeLinuxCNC()
        other = Controller(
            ini_path="/machine/machine.ini", module=other_module, cam_inbox=self.inbox
        )
        self.assertEqual(other.start_received(self.transfer)["state"], "unknown")
        self.assertEqual(other_module.calls, [])
        self.finish()
        self.assertEqual(other.start_received(self.transfer)["state"], "completed")
        self.assertEqual(other_module.calls, [])

    def test_stop_error_power_loss_and_foreign_writer_never_report_completion(self):
        for reason in ("stop", "error", "power", "foreign", "disconnect"):
            with self.subTest(reason=reason):
                if self.controller.received_status(self.transfer) is not None:
                    self.controller.close()
                    self.module = FakeLinuxCNC()
                    self.controller = Controller(
                        ini_path="/machine/machine.ini", module=self.module, cam_inbox=self.inbox
                    )
                    self.transfer = received(self.inbox)
                self.running()
                if reason == "stop":
                    self.controller.dispatch("program.stop")
                if reason == "error":
                    self.module.errors.append((self.module.NML_ERROR, "motion error"))
                if reason == "power":
                    self.module.status.enabled = False
                if reason == "foreign":
                    self.module.status.echo_serial_number += 10
                if reason == "disconnect":
                    self.module.available = False
                self.controller.poll()
                self.assertIn(
                    self.controller.received_status(self.transfer)["state"], ("unknown", "error")
                )


class CamExecutionNetworkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/tmp", prefix="cam-run-")
        self.root = Path(self.temp.name)
        self.inbox = self.root / "inbox"
        ProgramInbox(self.inbox)
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
        await asyncio.sleep(0.02)

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
                {"version": 2, "requestId": str(self.serial), "method": method, "params": params}
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
            connection, "upload.chunk", {"offset": 0, "data": base64.b64encode(body).decode()}
        )
        return await self.rpc(connection, "upload.finish", {})

    async def test_new_upload_runs_after_client_disconnect_and_receipt_retry_never_restarts(self):
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

    async def test_desktop_disconnect_preserves_service_job_and_existing_single_writer(self):
        reader, writer = await asyncio.open_unix_connection(str(self.control))
        request = json.dumps(
            {"version": 2, "request_id": "attach", "method": "session.attach", "params": {}}
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
