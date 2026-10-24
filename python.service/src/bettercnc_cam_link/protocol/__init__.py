"""Public CAM Link TCP framing and v2 request contract."""

from ._discovery import MAX_DISCOVERY_BYTES, decode_discovery, encode_discovery
from ._frames import (
    HEADER_BYTES,
    MAX_CHUNK_BYTES,
    MAX_FRAME_BYTES,
    PROTOCOL_VERSION,
    ProtocolError,
    Request,
    decode_chunk,
    encode_frame,
    read_request,
)

__all__ = [
    "HEADER_BYTES",
    "MAX_CHUNK_BYTES",
    "MAX_DISCOVERY_BYTES",
    "MAX_FRAME_BYTES",
    "PROTOCOL_VERSION",
    "ProtocolError",
    "Request",
    "decode_chunk",
    "decode_discovery",
    "encode_discovery",
    "encode_frame",
    "read_request",
]
