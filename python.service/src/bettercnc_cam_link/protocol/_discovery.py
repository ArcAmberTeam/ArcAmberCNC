"""Bounded UDP discovery envelopes; no transport, machine commands or credentials."""

import json
import re

from ._frames import (
    _DISCOVERY_TYPES,
    _HEADER,
    _MAGIC,
    HEADER_BYTES,
    PROTOCOL_VERSION,
    ProtocolError,
    _invalid_constant,
    _unique_object,
    encode_frame,
)

MAX_DISCOVERY_BYTES = 1024
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_BASE_FIELDS = {"version", "event", "service", "deviceId", "nonce"}
_SERVICE_FIELDS = {"deviceName", "tcpPort", "tls"}


def _validate(message, message_type):
    if not isinstance(message, dict):
        raise ValueError("discovery message must be an object")
    event = message.get("event")
    if not isinstance(event, str) or _DISCOVERY_TYPES.get(event) != message_type:
        raise ValueError("discovery header type differs from its event")
    if type(message.get("version")) is not int or message["version"] != PROTOCOL_VERSION:
        raise ValueError("unsupported discovery version")
    if message.get("service") != "bettercnc-cam-link":
        raise ValueError("unknown service")
    expected = _BASE_FIELDS.copy()
    if event != "discovery.reply":
        expected |= _SERVICE_FIELDS
    if event != "discovery.announce":
        expected.add("camId")
    if set(message) != expected:
        raise ValueError("discovery fields do not match this event")
    for key in ("deviceId", "camId"):
        if key in expected and (
            not isinstance(message[key], str) or not re.fullmatch(_UUID, message[key])
        ):
            raise ValueError(f"{key} must be a lowercase UUID")
    if not isinstance(message["nonce"], str) or not re.fullmatch(r"[0-9a-f]{32}", message["nonce"]):
        raise ValueError("nonce must contain 32 lowercase hex digits")
    if event != "discovery.reply":
        name = message["deviceName"]
        if (
            not isinstance(name, str)
            or not 1 <= len(name) <= 64
            or any(ord(character) < 32 or ord(character) == 127 for character in name)
        ):
            raise ValueError("deviceName must contain 1 to 64 printable characters")
        if type(message["tcpPort"]) is not int or not 1 <= message["tcpPort"] <= 65535:
            raise ValueError("tcpPort must be 1 to 65535")
        if type(message["tls"]) is not bool:
            raise ValueError("tls must be boolean")
    return message


def decode_discovery(data):
    """Validate exactly one complete CAM2 discovery frame inside one UDP datagram."""
    try:
        if not HEADER_BYTES < len(data) <= MAX_DISCOVERY_BYTES:
            raise ValueError("discovery datagram size must be 25 to 1024 bytes")
        magic, raw_type, size = _HEADER.unpack(data[:HEADER_BYTES])
        if magic != _MAGIC or size != len(data) - HEADER_BYTES:
            raise ValueError("discovery magic or length is invalid")
        message = json.loads(
            data[HEADER_BYTES:].decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
        )
        return _validate(message, raw_type.rstrip(b"\x00").decode("ascii"))
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ProtocolError("invalid_discovery", str(error)) from None


def encode_discovery(message):
    """Encode announcements, CAM replies or acknowledgements with their readable header."""
    packet = encode_frame(message)
    decode_discovery(packet)
    return packet
