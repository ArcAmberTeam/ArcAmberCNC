"""Receive bounded discovery replies, validating device and active challenge."""

import asyncio
import time
from collections import deque

from ..protocol import MAX_DISCOVERY_BYTES, ProtocolError, decode_discovery


class DiscoveryReceiver:
    """Accept only CAM replies to a recent announcement, with a bounded ACK rate."""

    def __init__(self, sock, *, device_id, valid_nonce):
        self._socket = sock
        self._device_id = device_id
        self._valid_nonce = valid_nonce
        self._recent = deque(maxlen=8)

    async def receive(self):
        loop = asyncio.get_running_loop()
        while True:
            data, address = await loop.sock_recvfrom(self._socket, MAX_DISCOVERY_BYTES + 1)
            # Even a stream of malformed datagrams must yield to TCP handlers.
            await asyncio.sleep(0)
            try:
                message = decode_discovery(data)
            except ProtocolError:
                continue
            if (
                message["event"] != "discovery.reply"
                or message["deviceId"] != self._device_id
                or not self._valid_nonce(message["nonce"])
            ):
                continue
            now = time.monotonic()
            while self._recent and now - self._recent[0] >= 1:
                self._recent.popleft()
            if len(self._recent) >= 8:
                continue
            self._recent.append(now)
            return message, address
