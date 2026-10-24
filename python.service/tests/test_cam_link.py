"""CAM Link through public services, real TCP framing, TLS and Unix feedback."""

import asyncio
import base64
import hashlib
import json
import os
import select
import socket
import ssl
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

from bettercnc_cam_link import serve
from bettercnc_cam_link.protocol import encode_frame
from betterlinuxcnc_service import serve as serve_control

REQUEST_TYPES = {
    "session.auth": "AUTH",
    "ping": "PING",
    "upload.begin": "SEND_GCODE",
    "upload.chunk": "SEND_GCODE",
    "upload.finish": "SEND_GCODE",
    "upload.abort": "ABORT_GCODE",
    "upload.receipt": "GET_RECEIPT",
    "status.get": "GET_STATUS",
    "status.subscribe": "SUB_STATUS",
    "status.unsubscribe": "UNSUB_STATUS",
}


def raw_frame(body, *, kind="REQUEST", magic=b"CAM2"):
    return struct.pack("!4s16sI", magic, kind.encode(), len(body)) + body


def frame(message, *, kind=None):
    kind = kind or REQUEST_TYPES.get(message.get("method"), "REQUEST")
    return raw_frame(json.dumps(message).encode(), kind=kind)


def request(request_id, method, params=None):
    return {"version": 2, "requestId": request_id, "method": method, "params": params or {}}


class Client:
    def __init__(self, reader, writer):
        self.reader, self.writer = reader, writer
        self.serial = 0
        self.events = []

    async def message(self):
        async with asyncio.timeout(4):
            magic, raw_type, size = struct.unpack("!4s16sI", await self.reader.readexactly(24))
            if magic != b"CAM2":
                raise AssertionError("response has the wrong CAM framing version")
            if not 0 < size <= 65536:
                raise AssertionError("response exceeds the frame budget")
            message = json.loads(await self.reader.readexactly(size))
            expected = (
                "STATUS" if "event" in message else "ERROR" if "error" in message else "REPLY"
            )
            if raw_type != expected.encode().ljust(16, b"\x00") or message.get("version") != 2:
                raise AssertionError("response header type or version differs from its body")
            return message

    async def rpc(self, method, params=None, *, request_id=None, fragment=False):
        self.serial += 1
        request_id = request_id or str(self.serial)
        data = frame(request(request_id, method, params))
        if fragment:
            for offset in range(0, len(data), 7):
                self.writer.write(data[offset : offset + 7])
                await self.writer.drain()
        else:
            self.writer.write(data)
            await self.writer.drain()
        while True:
            reply = await self.message()
            if "event" in reply:
                self.events.append(reply)
                continue
            if reply.get("requestId") != request_id:
                raise AssertionError("reply is not correlated with the request")
            return reply

    async def event(self):
        return self.events.pop(0) if self.events else await self.message()

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()


class CamLinkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/tmp", prefix="cam-")
        self.root = Path(self.temp.name)
        self.inbox = self.root / "inbox"
        self.control_socket = self.root / "control" / "control.sock"
        self.token = "test-token-" + "a" * 32
        self.stop = asyncio.Event()
        self.control_stop = asyncio.Event()
        self.clients = []
        self.readers = []
        self.feedback = {
            "connected": True,
            "programState": "running",
            "currentLine": 12,
            "taskLine": 100,
            "progressPercent": None,
            "file": "/machine/other.ngc",
        }
        test = self

        class Reader:
            def __init__(self, ini_path=None):
                self.closed = False
                test.readers.append(self)

            def poll(self):
                return dict(test.feedback)

            def close(self):
                self.closed = True

        def forbidden_controller(**kwargs):
            self.fail("CAM must not create a command-owning controller")

        self.control = asyncio.create_task(
            serve_control(
                self.control_socket,
                controller_factory=forbidden_controller,
                status_reader_factory=Reader,
                stop_event=self.control_stop,
            )
        )
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        self.address = listener.getsockname()
        self.server = asyncio.create_task(
            serve(
                self.inbox,
                token=self.token,
                control_socket=self.control_socket,
                max_bytes=1024 * 1024,
                io_timeout=1,
                idle_timeout=2,
                stop_event=self.stop,
                sock=listener,
            )
        )
        for _ in range(100):
            if self.server.done():
                await self.server
            if self.control_socket.exists() and self.inbox.exists():
                try:
                    client = await self.connect(auth=False)
                    await client.close()
                    break
                except ConnectionRefusedError:
                    pass
            await asyncio.sleep(0.01)
        else:
            self.fail("services did not start")

    async def asyncTearDown(self):
        self.stop.set()
        self.control_stop.set()
        await asyncio.wait_for(asyncio.gather(self.server, self.control), 5)
        for client in self.clients:
            await client.close()
        self.temp.cleanup()

    async def connect(self, *, auth=True):
        client = Client(*await asyncio.open_connection(*self.address))
        self.clients.append(client)
        if auth:
            result = await client.rpc("session.auth", {"token": self.token})
            self.assertTrue(result["result"]["authenticated"])
        return client

    def metadata(self, transfer_id, body=b"G0 X1\nM2\n", filename="part.ngc"):
        return {
            "transferId": transfer_id,
            "filename": filename,
            "size": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        }

    async def upload(self, client, transfer_id, body=b"G0 X1\nM2\n", *, fragment=False):
        result = await client.rpc("upload.begin", self.metadata(transfer_id, body))
        self.assertEqual(result["result"]["nextOffset"], 0)
        for offset in range(0, len(body), 32768):
            chunk = body[offset : offset + 32768]
            reply = await client.rpc(
                "upload.chunk",
                {"offset": offset, "data": base64.b64encode(chunk).decode()},
                fragment=fragment,
            )
            if "error" in reply:
                return reply
            self.assertEqual(reply["result"]["nextOffset"], offset + len(chunk))
        return await client.rpc("upload.finish")

    async def test_fragmented_upload_receipt_and_private_publication(self):
        client = await self.connect()
        transfer_id = str(uuid.uuid4())
        result = (await self.upload(client, transfer_id, fragment=True))["result"]
        self.assertEqual(result["state"], "received")
        self.assertFalse(result["duplicate"])
        target = self.inbox / transfer_id / "part.ngc"
        self.assertEqual(target.read_bytes(), b"G0 X1\nM2\n")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.inbox.stat().st_mode), 0o700)
        receipt = (await client.rpc("upload.receipt", {"transferId": transfer_id}))["result"]
        self.assertEqual(
            receipt, {key: value for key, value in result.items() if key != "duplicate"}
        )
        self.assertFalse(list(self.inbox.glob(".receiving-*")))
        self.assertEqual(self.readers, [])

    async def test_multiple_frames_in_one_write_preserve_boundaries(self):
        client = await self.connect()
        client.writer.write(frame(request("first", "ping")) + frame(request("second", "ping")))
        await client.writer.drain()
        self.assertEqual((await client.message())["requestId"], "first")
        self.assertEqual((await client.message())["requestId"], "second")

    async def test_gcode_header_is_readable_and_public_encoder_matches_wire_contract(self):
        client = await self.connect()
        message = request("file-header", "upload.begin", self.metadata(str(uuid.uuid4())))
        packet = encode_frame(message)
        self.assertEqual(packet[:20], b"CAM2SEND_GCODE" + b"\x00" * 6)
        self.assertEqual(struct.unpack("!I", packet[20:24])[0], len(packet) - 24)
        self.assertEqual(json.loads(packet[24:]), message)
        client.writer.write(packet)
        await client.writer.drain()
        reply = await client.message()
        self.assertEqual(reply["requestId"], "file-header")
        self.assertEqual(reply["result"]["state"], "receiving")
        await client.rpc("upload.abort")

    async def test_invalid_headers_and_header_body_mismatch_are_rejected(self):
        message = request("bad-header", "status.get")
        invalid = [
            (frame(message).replace(b"CAM2", b"CAM1", 1), "invalid_magic"),
            (frame(message, kind="UNKNOWN"), "invalid_message_type"),
            (frame(message, kind="SEND_GCODE"), "message_type_mismatch"),
            (frame(message, kind="REPLY"), "message_type_mismatch"),
            (frame(message).replace(b"GET_STATUS", b"GET\x00STATUS", 1), "invalid_message_type"),
            (frame(message).replace(b"GET_STATUS", b"\xffET_STATUS", 1), "invalid_message_type"),
            (struct.pack("!I", len(b"legacy")) + b"legacy" * 4, "invalid_magic"),
        ]
        for packet, code in invalid:
            with self.subTest(code=code):
                client = await self.connect()
                client.writer.write(packet)
                await client.writer.drain()
                reply = await client.message()
                self.assertEqual(reply["error"]["code"], code)
                if code == "message_type_mismatch":
                    self.assertEqual(reply["requestId"], "bad-header")
                self.assertEqual(await client.reader.read(), b"")
        self.assertEqual(self.readers, [])
        self.assertEqual(list(self.inbox.iterdir()), [])

    async def test_header_mismatch_aborts_pending_file_without_writing_the_chunk(self):
        client = await self.connect()
        await client.rpc("upload.begin", self.metadata(str(uuid.uuid4())))
        packet = frame(
            request("wrong-kind", "upload.chunk", {"offset": 0, "data": "RzAgWDEKTTIK"}),
            kind="GET_STATUS",
        )
        client.writer.write(packet)
        await client.writer.drain()
        self.assertEqual((await client.message())["error"]["code"], "message_type_mismatch")
        self.assertEqual(await client.reader.read(), b"")
        self.assertEqual(list(self.inbox.iterdir()), [])

    async def test_large_file_and_utf8_character_split_across_maximum_chunks(self):
        client = await self.connect()
        body = b";" + b"a" * 32766 + "中".encode() + b"\nM2\n"
        transfer_id = str(uuid.uuid4())
        result = (await self.upload(client, transfer_id, body))["result"]
        self.assertEqual(result["size"], len(body))
        self.assertEqual((self.inbox / transfer_id / "part.ngc").read_bytes(), body)

    async def test_retry_and_concurrent_duplicates_never_overwrite(self):
        first, second = await self.connect(), await self.connect()
        transfer_id = str(uuid.uuid4())
        replies = await asyncio.gather(
            self.upload(first, transfer_id), self.upload(second, transfer_id)
        )
        self.assertEqual(sorted(reply["result"]["duplicate"] for reply in replies), [False, True])
        conflict = await self.upload(first, transfer_id, b"G0 X9\nM2\n")
        self.assertEqual(conflict["error"]["code"], "transfer_id_conflict")
        self.assertEqual((self.inbox / transfer_id / "part.ngc").read_bytes(), b"G0 X1\nM2\n")

    async def test_authentication_is_required_and_does_not_expose_status_or_inbox(self):
        for method, params in (
            ("status.get", {}),
            ("upload.begin", self.metadata(str(uuid.uuid4()))),
            ("session.auth", {"token": "wrong"}),
        ):
            client = await self.connect(auth=False)
            result = await client.rpc(method, params)
            self.assertEqual(result["error"]["code"], "unauthorized")
            self.assertEqual(await client.reader.read(), b"")
        self.assertEqual(self.readers, [])
        self.assertEqual(list(self.inbox.iterdir()), [])

    async def test_metadata_validation_precedes_file_creation(self):
        client = await self.connect()
        for changes, expected in (
            ({"filename": "../part.ngc"}, "invalid_filename"),
            ({"filename": "%2e%2e%2fpart.ngc"}, "invalid_filename"),
            ({"size": 1048577}, "invalid_size"),
            ({"size": True}, "invalid_size"),
            ({"size": 0}, "invalid_size"),
            ({"sha256": "wrong"}, "invalid_sha256"),
            ({"transferId": "../outside"}, "invalid_transfer_id"),
        ):
            with self.subTest(changes=changes):
                params = {**self.metadata(str(uuid.uuid4())), **changes}
                self.assertEqual(
                    (await client.rpc("upload.begin", params))["error"]["code"], expected
                )
        self.assertEqual(list(self.inbox.iterdir()), [])

    async def test_bad_chunks_and_incomplete_files_abort_without_publishing(self):
        client = await self.connect()
        for body, offset, encoded, expected in (
            (b"M2\n", 1, "TTIK", "offset_mismatch"),
            (b"M2\n", 0, "!", "invalid_chunk"),
            (b"M2\n", 0, base64.b64encode(b"too long").decode(), "invalid_chunk_size"),
            (b"G0\x00X1", 0, base64.b64encode(b"G0\x00X1").decode(), "invalid_program"),
            (b"\xff", 0, "/w==", "invalid_program"),
        ):
            await client.rpc("upload.begin", self.metadata(str(uuid.uuid4()), body))
            reply = await client.rpc("upload.chunk", {"offset": offset, "data": encoded})
            self.assertEqual(reply["error"]["code"], expected)
            self.assertEqual(list(self.inbox.iterdir()), [])
        await client.rpc("upload.begin", self.metadata(str(uuid.uuid4())))
        self.assertEqual((await client.rpc("upload.finish"))["error"]["code"], "incomplete_program")
        await client.rpc("upload.begin", self.metadata(str(uuid.uuid4()), b"M2\n"))
        await client.rpc("upload.chunk", {"offset": 0, "data": "TTMK"})
        self.assertEqual((await client.rpc("upload.finish"))["error"]["code"], "sha256_mismatch")
        self.assertEqual(list(self.inbox.iterdir()), [])

    async def test_request_ids_prevent_repeated_writes(self):
        client = await self.connect()
        await client.rpc("upload.begin", self.metadata(str(uuid.uuid4()), b"M2\n"))
        params = {"offset": 0, "data": "TTIK"}
        await client.rpc("upload.chunk", params, request_id="only-once")
        duplicate = await client.rpc("upload.chunk", params, request_id="only-once")
        self.assertEqual(duplicate["error"]["code"], "duplicate_request")
        self.assertEqual((await client.rpc("upload.finish"))["result"]["size"], 3)

    async def test_invalid_envelopes_and_oversized_frames_close_the_connection(self):
        invalid = [
            (frame(request("wrong", "ping") | {"version": True}), "unsupported_version"),
            (frame(request("old-version", "ping") | {"version": 1}), "unsupported_version"),
            (frame(request("extra", "ping") | {"extra": 1}), "invalid_request"),
            (
                frame({"version": 2, "requestId": "x", "method": "ping", "params": []}),
                "invalid_request",
            ),
        ]
        for payload in (
            json.dumps(request("wrong-encoding", "ping")).encode("utf-16"),
            b'{"version":2,"requestId":"x","method":"ping","method":"status.get","params":{}}',
            b'{"version":2,"requestId":"x","method":"ping","params":{"x":NaN}}',
            b"[" * 3000 + b"]" * 3000,
        ):
            invalid.append((raw_frame(payload), "invalid_request"))
        invalid.extend(
            (struct.pack("!4s16sI", b"CAM2", b"PING", length), "invalid_frame")
            for length in (0, 65537)
        )
        for data, code in invalid:
            with self.subTest(code=code):
                client = await self.connect()
                client.writer.write(data)
                await client.writer.drain()
                self.assertEqual((await client.message())["error"]["code"], code)
                self.assertEqual(await client.reader.read(), b"")

    async def test_disconnect_timeout_and_explicit_abort_clean_partial_uploads(self):
        client = await self.connect()
        await client.rpc("upload.begin", self.metadata(str(uuid.uuid4())))
        await client.rpc("upload.abort")
        self.assertEqual(list(self.inbox.iterdir()), [])
        await client.rpc("upload.begin", self.metadata(str(uuid.uuid4())))
        client.writer.write(struct.pack("!4s16sI", b"CAM2", b"SEND_GCODE", 100) + b"{")
        await client.writer.drain()
        self.assertEqual(await asyncio.wait_for(client.reader.read(), 3), b"")
        self.assertEqual(list(self.inbox.iterdir()), [])
        client = await self.connect()
        await client.rpc("upload.begin", self.metadata(str(uuid.uuid4())))
        await client.close()
        for _ in range(100):
            if not list(self.inbox.iterdir()):
                break
            await asyncio.sleep(0.01)
        self.assertEqual(list(self.inbox.iterdir()), [])

    async def test_feedback_is_fresh_and_correlates_program_without_acquiring_control(self):
        client = await self.connect()
        transfer_id = str(uuid.uuid4())
        await self.upload(client, transfer_id)
        self.feedback["file"] = str(self.inbox / transfer_id / "part.ngc")
        status = (await client.rpc("status.get"))["result"]
        self.assertEqual(status["transferId"], transfer_id)
        self.assertEqual(status["currentLine"], 12)
        self.assertEqual(status["taskLine"], 100)
        self.assertIsNone(status["progressPercent"])
        self.feedback.update(programState="paused", currentLine=14)
        status = (await client.rpc("status.get"))["result"]
        self.assertEqual(status["programState"], "paused")
        self.assertEqual(status["currentLine"], 14)
        self.assertEqual(len(self.readers), 1)
        self.assertEqual((await client.rpc("program.run"))["error"]["code"], "unsupported_method")
        self.control_stop.set()
        await self.control
        self.assertTrue(self.readers[0].closed)
        self.assertEqual(
            (await client.rpc("status.get"))["error"]["code"], "controller_unavailable"
        )

    async def test_subscription_pushes_while_uploading_and_unsubscribe_stops_events(self):
        client = await self.connect()
        result = await client.rpc("status.subscribe", {"interval": 1})
        self.assertTrue(result["result"]["subscribed"])
        event = await client.event()
        self.assertEqual(event["event"], "machine.status")
        self.assertEqual(event["data"]["currentLine"], 12)
        transfer_id = str(uuid.uuid4())
        await client.rpc("upload.begin", self.metadata(transfer_id))
        self.feedback["currentLine"] = 20
        event = await client.event()
        self.assertEqual(event["data"]["currentLine"], 20)
        await client.rpc("upload.chunk", {"offset": 0, "data": "RzAgWDEKTTIK"})
        self.assertEqual((await client.rpc("upload.finish"))["result"]["state"], "received")
        self.assertFalse((await client.rpc("status.unsubscribe"))["result"]["subscribed"])
        client.events.clear()
        self.assertTrue((await client.rpc("ping"))["result"]["alive"])
        with self.assertRaises(TimeoutError):
            await asyncio.wait_for(client.message(), 0.1)

    async def test_subscription_reports_failure_and_recovers_on_the_same_connection(self):
        client = await self.connect()
        self.feedback.update(connected=False, programState="unknown", currentLine=None)
        await client.rpc("status.subscribe", {"interval": 1})
        event = await client.event()
        self.assertFalse(event["data"]["connected"])
        self.assertIsNone(event["data"]["currentLine"])
        self.feedback.update(connected=True, programState="running", currentLine=42)
        self.assertEqual((await client.event())["data"]["currentLine"], 42)
        await client.rpc("status.unsubscribe")
        self.control_stop.set()
        await self.control
        await client.rpc("status.subscribe", {"interval": 1})
        event = await client.event()
        self.assertEqual(event["error"]["code"], "controller_unavailable")
        self.assertNotIn("data", event)

    async def test_connection_limit_releases_slots(self):
        for _ in range(4):
            await self.connect()
        client = await self.connect(auth=False)
        self.assertEqual(await asyncio.wait_for(client.reader.read(), 0.5), b"")
        for client in self.clients:
            await client.close()
        await asyncio.sleep(0.02)
        self.assertTrue((await (await self.connect()).rpc("ping"))["result"]["alive"])

    async def test_shutdown_cleans_partial_upload_and_subscription(self):
        client = await self.connect()
        await client.rpc("status.subscribe", {"interval": 1})
        await client.rpc("upload.begin", self.metadata(str(uuid.uuid4())))
        self.assertTrue(list(self.inbox.glob(".receiving-*")))
        self.stop.set()
        await self.server
        self.assertEqual(list(self.inbox.iterdir()), [])
        # An already buffered event may precede EOF, but no session survives shutdown.
        await asyncio.wait_for(client.reader.read(), 2)


class CamLinkCliTests(unittest.TestCase):
    def test_installed_command_accepts_tls_tcp_and_shuts_down_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cert, key = root / "cert.pem", root / "key.pem"
            subprocess.run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-keyout",
                    str(key),
                    "-out",
                    str(cert),
                    "-days",
                    "1",
                    "-subj",
                    "/CN=localhost",
                ],
                capture_output=True,
                check=True,
                timeout=15,
            )
            token = "test-token-" + "a" * 32
            token_file = root / "token"
            token_file.write_text(token)
            os.chmod(token_file, 0o600)
            process = subprocess.Popen(
                [
                    str(Path(sys.executable).with_name("betterlinuxcnc-cam-link")),
                    "--inbox",
                    str(root / "inbox"),
                    "--control-socket",
                    str(root / "missing.sock"),
                    "--token-file",
                    str(token_file),
                    "--port",
                    "0",
                    "--cert",
                    str(cert),
                    "--key",
                    str(key),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                self.assertTrue(select.select([process.stdout], [], [], 5)[0], "CLI not ready")
                address = json.loads(process.stdout.readline())
                context = ssl.create_default_context(cafile=cert)
                with socket.create_connection(("localhost", address["port"]), timeout=5) as raw:
                    with context.wrap_socket(raw, server_hostname="localhost") as connection:
                        stream = connection.makefile("rb")
                        try:
                            for number, method, params in (
                                (1, "session.auth", {"token": token}),
                                (2, "ping", {}),
                            ):
                                connection.sendall(frame(request(str(number), method, params)))
                                magic, kind, size = struct.unpack("!4s16sI", stream.read(24))
                                self.assertEqual(magic, b"CAM2")
                                self.assertEqual(kind, b"REPLY".ljust(16, b"\x00"))
                                reply = json.loads(stream.read(size))
                                self.assertIn("result", reply)
                        finally:
                            stream.close()
                process.terminate()
                self.assertEqual(process.wait(timeout=5), 0)
                self.assertEqual(process.stderr.read(), b"")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
                process.stdout.close()
                process.stderr.close()

    def test_installed_cli_validates_configuration_and_module_entrypoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token = root / "token"
            token.write_text("a" * 32)
            os.chmod(token, 0o644)
            command = [
                sys.executable,
                "-m",
                "bettercnc_cam_link",
                "--inbox",
                str(root / "inbox"),
                "--control-socket",
                str(root / "control.sock"),
                "--token-file",
                str(token),
            ]
            result = subprocess.run(command, capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"token file", result.stderr)
            os.chmod(token, 0o600)
            result = subprocess.run(command + ["--max-bytes", "0"], capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"max_bytes", result.stderr)
            self.assertEqual(
                subprocess.run(
                    [sys.executable, "-m", "bettercnc_cam_link", "--help"],
                    capture_output=True,
                    timeout=5,
                ).returncode,
                0,
            )


if __name__ == "__main__":
    unittest.main()
