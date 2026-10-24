"""Typed CAM2 frame headers and strict JSON; no business or platform dependencies."""

import asyncio
import base64
import binascii
import json
import struct
from dataclasses import dataclass

MAX_FRAME_BYTES = 65536
MAX_CHUNK_BYTES = 32768
PROTOCOL_VERSION = 2
HEADER_BYTES = 24
_HEADER = struct.Struct("!4s16sI")
_MAGIC = b"CAM2"
_REQUEST_TYPES = {
    "session.auth": "AUTH",
    "ping": "PING",
    "jog.start": "JOG_START",
    "jog.keepalive": "JOG_KEEPALIVE",
    "jog.stop": "JOG_STOP",
    "upload.begin": "SEND_GCODE",
    "upload.chunk": "SEND_GCODE",
    "upload.finish": "SEND_GCODE",
    "upload.abort": "ABORT_GCODE",
    "upload.receipt": "GET_RECEIPT",
    "job.start": "START_JOB",
    "job.status": "GET_JOB",
    "status.get": "GET_STATUS",
    "status.subscribe": "SUB_STATUS",
    "status.unsubscribe": "UNSUB_STATUS",
}
_MESSAGE_TYPES = set(_REQUEST_TYPES.values()) | {"REQUEST", "REPLY", "ERROR", "STATUS"}
_DISCOVERY_TYPES = {
    "discovery.announce": "ANNOUNCE",
    "discovery.reply": "DISCOVER_REPLY",
    "discovery.ack": "DISCOVER_ACK",
}


class ProtocolError(ValueError):
    def __init__(self, code, message, request_id=""):
        super().__init__(message)
        self.code = code
        self.request_id = request_id


@dataclass(frozen=True)
class Request:
    request_id: str
    method: str
    params: dict


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def _message_type(message):
    if isinstance(message.get("method"), str):
        return _REQUEST_TYPES.get(message["method"], "REQUEST")
    if message.get("event") == "machine.status":
        return "STATUS"
    event = message.get("event")
    if isinstance(event, str) and event in _DISCOVERY_TYPES:
        return _DISCOVERY_TYPES[event]
    if "requestId" in message:
        if "error" in message:
            return "ERROR"
        if "result" in message:
            return "REPLY"
    raise ProtocolError(
        "invalid_message", "message must be a request, reply or machine status event"
    )


def encode_frame(message):
    """Encode a CAM2 header with a readable ASCII message type and bounded JSON body."""
    if (
        not isinstance(message, dict)
        or type(message.get("version")) is not int
        or message["version"] != PROTOCOL_VERSION
    ):
        raise ProtocolError("unsupported_version", "supported CAM TCP version: 2")
    message_type = _message_type(message)
    body = json.dumps(message, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    if not 0 < len(body) <= MAX_FRAME_BYTES:
        raise ProtocolError("frame_too_large", "frame exceeds 65536 bytes")
    return _HEADER.pack(_MAGIC, message_type.encode("ascii"), len(body)) + body


async def read_request(reader, *, idle_timeout=60.0, io_timeout=10.0):
    """Read one request; invalid framing or envelopes require closing the connection."""
    async with asyncio.timeout(idle_timeout):
        magic, raw_type, size = _HEADER.unpack(await reader.readexactly(HEADER_BYTES))
    if magic != _MAGIC:
        raise ProtocolError("invalid_magic", "frame must start with CAM2")
    try:
        message_type = raw_type.rstrip(b"\x00").decode("ascii")
    except UnicodeError:
        raise ProtocolError("invalid_message_type", "message type must be ASCII") from None
    if message_type not in _MESSAGE_TYPES:
        raise ProtocolError("invalid_message_type", "unknown message type")
    if not 0 < size <= MAX_FRAME_BYTES:
        raise ProtocolError("invalid_frame", "frame length must be 1 to 65536 bytes")
    async with asyncio.timeout(io_timeout):
        payload = await reader.readexactly(size)
    request_id = ""
    try:
        message = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
        )
        if not isinstance(message, dict):
            raise ValueError("request must be an object")
        candidate = message.get("requestId")
        if not isinstance(candidate, str) or not 1 <= len(candidate) <= 64:
            raise ValueError("requestId must contain 1 to 64 characters")
        request_id = candidate
        if type(message.get("version")) is not int or message["version"] != PROTOCOL_VERSION:
            raise ProtocolError("unsupported_version", "supported CAM TCP version: 2", request_id)
        if set(message) != {"version", "requestId", "method", "params"}:
            raise ValueError("request fields do not match the protocol")
        if not isinstance(message["method"], str) or not message["method"]:
            raise ValueError("method must be a nonempty string")
        if not isinstance(message["params"], dict):
            raise ValueError("params must be an object")
        if message_type != _REQUEST_TYPES.get(message["method"], "REQUEST"):
            raise ProtocolError(
                "message_type_mismatch", "header type does not match the request method", request_id
            )
        return Request(request_id, message["method"], message["params"])
    except ProtocolError:
        raise
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ProtocolError("invalid_request", str(error), request_id) from None


def decode_chunk(data):
    """Decode at most 32 KiB of G-code carried as strict Base64 in a JSON frame."""
    if not isinstance(data, str) or not 0 < len(data) <= 4 * ((MAX_CHUNK_BYTES + 2) // 3):
        raise ProtocolError("invalid_chunk", "chunk must contain 1 to 32768 decoded bytes")
    try:
        chunk = base64.b64decode(data, validate=True)
    except (ValueError, binascii.Error):
        raise ProtocolError("invalid_chunk", "chunk data must be Base64") from None
    if not 0 < len(chunk) <= MAX_CHUNK_BYTES:
        raise ProtocolError("invalid_chunk", "chunk must contain 1 to 32768 decoded bytes")
    return chunk
