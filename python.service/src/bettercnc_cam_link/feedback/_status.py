"""Read the public local protocol without acquiring a control session."""

import asyncio
import contextlib
import json
import struct
import uuid


async def machine_status(path):
    writer = None
    try:
        async with asyncio.timeout(2):
            reader, writer = await asyncio.open_unix_connection(str(path), limit=65536)
            request_id = uuid.uuid4().hex
            body = json.dumps(
                {"version": 2, "request_id": request_id, "method": "machine.status", "params": {}}
            ).encode()
            writer.write(struct.pack("!I", len(body)) + body)
            await writer.drain()
            size = struct.unpack("!I", await reader.readexactly(4))[0]
            if not 0 < size <= 65536:
                raise ValueError("invalid local status frame")
            reply = json.loads(await reader.readexactly(size))
            if (
                not isinstance(reply, dict)
                or reply.get("version") != 2
                or reply.get("request_id") != request_id
                or not isinstance(reply.get("result"), dict)
            ):
                raise ValueError("local status unavailable")
            return reply["result"]
    finally:
        if writer is not None:
            writer.close()
            with contextlib.suppress(ConnectionError, OSError):
                await writer.wait_closed()
