"""Broadcast machine availability and acknowledge discovery handshakes."""

import asyncio
import hmac
import secrets
import time
from collections import deque

from ..protocol import PROTOCOL_VERSION, encode_discovery


class DiscoverySender:
    """Own discovery announcements, short-lived challenges and outbound ACKs.

    No token, file contents or machine state is included in these public packets.
    UDP discovery is an address hint; the TCP client must still authenticate.
    """

    def __init__(self, sock, *, device_id, device_name, tcp_port, tls, target, interval):
        self._socket = sock
        self._target = target
        self._interval = interval
        self._nonces = deque(maxlen=3)
        self._identity = {
            "version": PROTOCOL_VERSION,
            "service": "bettercnc-cam-link",
            "deviceId": device_id,
            "deviceName": device_name,
            "tcpPort": tcp_port,
            "tls": tls,
        }

    def accepts(self, nonce):
        now = time.monotonic()
        return any(
            now - created < 3 * self._interval and hmac.compare_digest(nonce, candidate)
            for candidate, created in self._nonces
        )

    async def publish(self):
        loop = asyncio.get_running_loop()
        while True:
            nonce = secrets.token_hex(16)
            packet = encode_discovery(
                {**self._identity, "event": "discovery.announce", "nonce": nonce}
            )
            self._nonces.append((nonce, time.monotonic()))
            await loop.sock_sendto(self._socket, packet, self._target)
            await asyncio.sleep(self._interval)

    async def acknowledge(self, reply, address):
        packet = encode_discovery(
            {
                **self._identity,
                "event": "discovery.ack",
                "nonce": reply["nonce"],
                "camId": reply["camId"],
            }
        )
        await asyncio.get_running_loop().sock_sendto(self._socket, packet, address)
