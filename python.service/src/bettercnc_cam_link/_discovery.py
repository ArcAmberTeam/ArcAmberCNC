"""Compose optional LAN discovery without adding another capability directory."""

import asyncio
import ipaddress
import math
import socket
from dataclasses import dataclass

from .feedback import DiscoverySender
from .protocol import PROTOCOL_VERSION, encode_discovery
from .receiver import DiscoveryReceiver


@dataclass(frozen=True)
class DiscoveryOptions:
    """Explicit identity and UDP network configuration for machine announcements.

    CAM listens on port; replies go to the announcement's source IP and UDP port.
    bind_port defaults to port. A distinct value supports an embedding host.
    """

    device_id: str
    device_name: str = "LinuxCNC"
    address: str = "255.255.255.255"
    port: int = 8421
    bind_port: int | None = None
    interval: float = 3.0

    def validate(self):
        ipaddress.IPv4Address(self.address)
        for port in (self.port, self.port if self.bind_port is None else self.bind_port):
            if type(port) is not int or not 0 <= port <= 65535:
                raise ValueError("discovery UDP ports must be integers between 0 and 65535")
        if self.port == 0:
            raise ValueError("discovery destination port must be nonzero")
        if (
            type(self.interval) not in (int, float)
            or not math.isfinite(self.interval)
            or not 0.1 <= self.interval <= 60
        ):
            raise ValueError("discovery interval must be 0.1 to 60 seconds")
        # Reuse the wire contract to validate identity without a second schema.
        encode_discovery(
            {
                "version": PROTOCOL_VERSION,
                "event": "discovery.announce",
                "service": "bettercnc-cam-link",
                "deviceId": self.device_id,
                "deviceName": self.device_name,
                "tcpPort": 6522,
                "tls": False,
                "nonce": "0" * 32,
            }
        )


async def run_discovery(options, *, tcp_address, tls, ready):
    host, port = tcp_address[:2]
    if (
        ipaddress.IPv4Address(host).is_loopback
        and not ipaddress.IPv4Address(options.address).is_loopback
    ):
        raise ValueError("LAN discovery needs --host 0.0.0.0 or a LAN IPv4 address")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tasks = []
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind((host, options.port if options.bind_port is None else options.bind_port))
        sock.setblocking(False)
        sender = DiscoverySender(
            sock,
            device_id=options.device_id,
            device_name=options.device_name,
            tcp_port=port,
            tls=tls,
            target=(options.address, options.port),
            interval=options.interval,
        )
        receiver = DiscoveryReceiver(sock, device_id=options.device_id, valid_nonce=sender.accepts)

        async def handshakes():
            while True:
                message, peer = await receiver.receive()
                await sender.acknowledge(message, peer)

        tasks = [asyncio.create_task(sender.publish()), asyncio.create_task(handshakes())]
        ready.set_result(None)
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        sock.close()
