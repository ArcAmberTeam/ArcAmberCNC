"""Discover machines without configured IPs using public APIs and real loopback UDP/TCP."""

import asyncio
import json
import os
import select
import socket
import struct
import subprocess
import sys
import tempfile
import unittest
import uuid
from dataclasses import replace
from pathlib import Path

from bettercnc_cam_link import DiscoveryOptions, serve
from bettercnc_cam_link.protocol import (
    ProtocolError,
    decode_discovery,
    encode_discovery,
    encode_frame,
)


def wire(message, kind="DISCOVER_REPLY"):
    body = json.dumps(message).encode()
    return struct.pack("!4s16sI", b"CAM2", kind.encode(), len(body)) + body


def announcement():
    return {
        "version": 2,
        "event": "discovery.announce",
        "service": "bettercnc-cam-link",
        "deviceId": "550e8400-e29b-41d4-a716-446655440000",
        "deviceName": "机床一号",
        "tcpPort": 6522,
        "tls": False,
        "nonce": "a" * 32,
    }


def reply_to(message, cam_id):
    return {
        "version": 2,
        "event": "discovery.reply",
        "service": "bettercnc-cam-link",
        "deviceId": message["deviceId"],
        "nonce": message["nonce"],
        "camId": cam_id,
    }


class DiscoveryProtocolTests(unittest.TestCase):
    def test_readable_discovery_headers_and_round_trip(self):
        offer = announcement()
        reply = reply_to(offer, str(uuid.uuid4()))
        ack = {**offer, "event": "discovery.ack", "camId": reply["camId"]}
        for message, kind in (
            (offer, "ANNOUNCE"),
            (reply, "DISCOVER_REPLY"),
            (ack, "DISCOVER_ACK"),
        ):
            with self.subTest(kind=kind):
                packet = encode_discovery(message)
                self.assertEqual(packet[:20], b"CAM2" + kind.encode().ljust(16, b"\x00"))
                self.assertLessEqual(len(packet), 1024)
                self.assertEqual(decode_discovery(packet), message)

    def test_malformed_or_unrelated_datagrams_are_rejected(self):
        offer = announcement()
        packet = encode_discovery(offer)
        invalid = [
            b"",
            packet[:20],
            packet + b"extra",
            packet + packet,
            b"x" * 1025,
            packet.replace(b"CAM2", b"CAM1", 1),
            packet.replace(b"ANNOUNCE", b"UNKNOWN!", 1),
            wire(reply_to(offer, str(uuid.uuid4())), kind="ANNOUNCE"),
        ]
        for changes in (
            {"service": "another-service"},
            {"deviceId": "invalid"},
            {"nonce": "0"},
            {"tcpPort": True},
            {"tcpPort": 0},
            {"tls": 1},
            {"deviceName": "line\nbreak"},
            {"token": "never-disclose"},
            {"event": []},
            {"version": True},
        ):
            invalid.append(wire({**offer, **changes}, kind="ANNOUNCE"))
        for data in invalid:
            with self.subTest(data=data[:60]):
                with self.assertRaises(ProtocolError):
                    decode_discovery(data)

    def test_config_validation_is_explicit(self):
        options = DiscoveryOptions(device_id=announcement()["deviceId"])
        options.validate()
        for changes in (
            {"device_id": "invalid"},
            {"port": 0},
            {"port": True},
            {"bind_port": -1},
            {"address": "not-an-ip"},
            {"interval": 0},
            {"interval": float("inf")},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(options, **changes).validate()


class DiscoveryServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/tmp", prefix="cam-discovery-")
        self.root = Path(self.temp.name)
        self.cam = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cam.bind(("127.0.0.1", 0))
        self.cam.setblocking(False)
        self.stop = asyncio.Event()
        self.cam_id = str(uuid.uuid4())
        self.token = "a" * 32
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        self.tcp_address = listener.getsockname()
        self.options = DiscoveryOptions(
            device_id=str(uuid.uuid4()),
            device_name="机床一号",
            address="127.0.0.1",
            port=self.cam.getsockname()[1],
            bind_port=0,
            interval=0.2,
        )
        self.server = asyncio.create_task(
            serve(
                self.root / "inbox",
                token=self.token,
                control_socket=self.root / "missing.sock",
                stop_event=self.stop,
                sock=listener,
                discovery=self.options,
            )
        )
        self.first, self.peer, self.packet = await self.datagram("discovery.announce")

    async def asyncTearDown(self):
        self.stop.set()
        await asyncio.wait_for(self.server, 5)
        self.cam.close()
        self.temp.cleanup()

    async def datagram(self, event=None, *, sock=None, timeout=2):
        async with asyncio.timeout(timeout):
            while True:
                packet, address = await asyncio.get_running_loop().sock_recvfrom(
                    sock or self.cam, 1025
                )
                message = decode_discovery(packet)
                if event is None or message["event"] == event:
                    return message, address, packet

    async def send(self, message, *, sock=None, raw=False):
        packet = message if raw else encode_discovery(message)
        await asyncio.get_running_loop().sock_sendto(sock or self.cam, packet, self.peer)

    async def no_ack(self, duration=0.07):
        try:
            await self.datagram("discovery.ack", timeout=duration)
        except TimeoutError:
            return
        self.fail("invalid discovery reply received an ACK")

    async def latest_announcement(self):
        message, _, _ = await self.datagram("discovery.announce")
        while True:
            try:
                message, _, _ = await self.datagram("discovery.announce", timeout=0.01)
            except TimeoutError:
                return message

    async def tcp_request(self, reader, writer, request_id, method, params=None):
        writer.write(
            encode_frame(
                {
                    "version": 2,
                    "requestId": request_id,
                    "method": method,
                    "params": params or {},
                }
            )
        )
        await writer.drain()
        async with asyncio.timeout(2):
            magic, _, size = struct.unpack("!4s16sI", await reader.readexactly(24))
            self.assertEqual(magic, b"CAM2")
            return json.loads(await reader.readexactly(size))

    async def test_cam_learns_ip_handshakes_then_authenticates_tcp(self):
        self.assertEqual(self.first["deviceId"], self.options.device_id)
        self.assertEqual(self.first["tcpPort"], self.tcp_address[1])
        self.assertEqual(self.first["deviceName"], "机床一号")
        self.assertFalse(self.first["tls"])
        self.assertNotIn(self.token.encode(), self.packet)
        await self.send(reply_to(self.first, self.cam_id))
        ack, source, _ = await self.datagram("discovery.ack")
        self.assertEqual(source, self.peer)
        self.assertEqual(ack["camId"], self.cam_id)
        self.assertEqual(ack["nonce"], self.first["nonce"])
        # IP comes from recvfrom, TCP port from the reply, not user configuration.
        reader, writer = await asyncio.open_connection(source[0], ack["tcpPort"])
        try:
            auth = await self.tcp_request(
                reader, writer, "auth", "session.auth", {"token": self.token}
            )
            self.assertTrue(auth["result"]["authenticated"])
            self.assertTrue(
                (await self.tcp_request(reader, writer, "ping", "ping"))["result"]["alive"]
            )
        finally:
            writer.close()
            await writer.wait_closed()
        self.assertFalse((self.root / "missing.sock").exists())

    async def test_discovery_handshake_does_not_grant_tcp_authentication(self):
        await self.send(reply_to(self.first, self.cam_id))
        ack, source, _ = await self.datagram("discovery.ack")
        reader, writer = await asyncio.open_connection(source[0], ack["tcpPort"])
        try:
            result = await self.tcp_request(reader, writer, "no-auth", "ping")
            self.assertEqual(result["error"]["code"], "unauthorized")
            self.assertEqual(await reader.read(), b"")
        finally:
            writer.close()
            await writer.wait_closed()

    async def test_invalid_replies_are_silent_and_do_not_create_programs(self):
        valid = reply_to(self.first, self.cam_id)
        for message in (
            {**valid, "nonce": "0" * 32},
            {**valid, "deviceId": str(uuid.uuid4())},
        ):
            await self.send(message)
        for raw in (b"invalid", b"x" * 1025, wire({**valid, "token": "secret"})):
            await self.send(raw, raw=True)
        await self.send(self.first)  # Ignore our own broadcast returning on the UDP socket.
        await self.no_ack()
        self.assertEqual(list((self.root / "inbox").iterdir()), [])
        current = await self.latest_announcement()
        await self.send(reply_to(current, self.cam_id))
        self.assertEqual((await self.datagram("discovery.ack"))[0]["camId"], self.cam_id)

    async def test_expired_nonce_is_rejected_and_current_nonce_still_works(self):
        await asyncio.sleep(0.75)
        await self.send(reply_to(self.first, self.cam_id))
        await self.no_ack()
        current = await self.latest_announcement()
        self.assertNotEqual(current["nonce"], self.first["nonce"])
        await self.send(reply_to(current, self.cam_id))
        self.assertEqual((await self.datagram("discovery.ack"))[0]["nonce"], current["nonce"])

    async def test_multiple_cams_get_unicast_acknowledgements(self):
        other = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        other.bind(("127.0.0.1", 0))
        other.setblocking(False)
        try:
            other_id = str(uuid.uuid4())
            await self.send(reply_to(self.first, self.cam_id))
            await self.send(reply_to(self.first, other_id), sock=other)
            first_ack, _, _ = await self.datagram("discovery.ack")
            other_ack, _, _ = await self.datagram("discovery.ack", sock=other)
            self.assertEqual(first_ack["camId"], self.cam_id)
            self.assertEqual(other_ack["camId"], other_id)
        finally:
            other.close()

    async def test_announcements_repeat_and_shutdown_releases_udp_and_tcp(self):
        current = await self.latest_announcement()
        self.assertNotEqual(current["nonce"], self.first["nonce"])
        self.assertEqual(current["deviceId"], self.first["deviceId"])
        self.stop.set()
        await self.server
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.bind(self.peer)
        finally:
            probe.close()
        with self.assertRaises(ConnectionRefusedError):
            await asyncio.open_connection(*self.tcp_address)

    async def test_discovery_port_conflict_closes_the_new_tcp_listener(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        address = listener.getsockname()
        options = replace(self.options, bind_port=self.cam.getsockname()[1])
        with self.assertRaises(OSError):
            await asyncio.wait_for(
                serve(
                    self.root / "inbox",
                    token=self.token,
                    control_socket=self.root / "missing.sock",
                    stop_event=asyncio.Event(),
                    sock=listener,
                    discovery=options,
                ),
                2,
            )
        with self.assertRaises(ConnectionRefusedError):
            await asyncio.open_connection(*address)

    async def test_discovery_acknowledgements_are_rate_limited(self):
        for _ in range(16):
            await self.send(reply_to(self.first, str(uuid.uuid4())))
        acknowledgements = 0
        try:
            async with asyncio.timeout(0.1):
                while True:
                    await self.datagram("discovery.ack")
                    acknowledgements += 1
        except TimeoutError:
            pass
        self.assertEqual(acknowledgements, 8)
        await asyncio.sleep(1)
        current = await self.latest_announcement()
        await self.send(reply_to(current, self.cam_id))
        self.assertEqual((await self.datagram("discovery.ack"))[0]["camId"], self.cam_id)


class DiscoveryCliTests(unittest.TestCase):
    def test_installed_cli_announces_and_acknowledges(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token = root / "token"
            token.write_text("a" * 32)
            os.chmod(token, 0o600)
            cam = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            cam.bind(("127.0.0.1", 0))
            cam.settimeout(4)
            device_id = str(uuid.uuid4())
            command = [
                str(Path(sys.executable).with_name("betterlinuxcnc-cam-link")),
                "--inbox",
                str(root / "inbox"),
                "--token-file",
                str(token),
                "--control-socket",
                str(root / "missing.sock"),
                "--port",
                "0",
                "--discover",
                "--device-id",
                device_id,
                "--device-name",
                "Test CNC",
                "--discovery-address",
                "127.0.0.1",
                "--discovery-port",
                str(cam.getsockname()[1]),
                "--discovery-bind-port",
                "0",
            ]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                self.assertTrue(select.select([process.stdout], [], [], 5)[0], "CLI not ready")
                address = json.loads(process.stdout.readline())
                packet, source = cam.recvfrom(1025)
                offer = decode_discovery(packet)
                self.assertEqual(offer["tcpPort"], address["port"])
                self.assertEqual(offer["deviceId"], device_id)
                self.assertEqual(offer["deviceName"], "Test CNC")
                cam.sendto(encode_discovery(reply_to(offer, str(uuid.uuid4()))), source)
                ack = decode_discovery(cam.recvfrom(1025)[0])
                self.assertEqual(ack["event"], "discovery.ack")
                process.terminate()
                self.assertEqual(process.wait(timeout=5), 0)
                self.assertEqual(process.stderr.read(), b"")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
                process.stdout.close()
                process.stderr.close()
                cam.close()


if __name__ == "__main__":
    unittest.main()
