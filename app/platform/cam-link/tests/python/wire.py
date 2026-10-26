"""Independent CAM client wire fixtures; no production server implementation imports."""

import json
import struct

KINDS = {
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
    "job.start": "START_JOB",
    "job.status": "GET_JOB",
    "jog.start": "JOG_START",
    "jog.keepalive": "JOG_KEEPALIVE",
    "jog.stop": "JOG_STOP",
    "discovery.announce": "ANNOUNCE",
    "discovery.reply": "DISCOVER_REPLY",
    "discovery.ack": "DISCOVER_ACK",
}


def encode_frame(message):
    body = json.dumps(message, ensure_ascii=False).encode()
    kind = KINDS.get(message.get("method", message.get("event")), "REQUEST")
    return struct.pack("!4s16sI", b"CAM2", kind.encode(), len(body)) + body


encode_discovery = encode_frame


def decode_discovery(packet):
    magic, kind, size = struct.unpack("!4s16sI", packet[:24])
    assert magic == b"CAM2" and len(packet) == 24 + size and len(packet) <= 1024
    message = json.loads(packet[24:])
    assert kind.rstrip(b"\x00").decode() == KINDS[message["event"]]
    return message
