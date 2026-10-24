"""Serialize replies and subscription events; read machine feedback via public IPC."""

import asyncio
import contextlib

from ..protocol import PROTOCOL_VERSION, encode_frame
from ._status import machine_status


class FeedbackError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class FeedbackChannel:
    """Own outbound frames so replies and pushed events never interleave bytes.

    identify_program is supplied by the composition root; feedback never reads
    the receiver's private files or acquires a machine control session.
    """

    def __init__(self, writer, *, control_socket, identify_program, io_timeout=10.0):
        self._writer = writer
        self._socket = control_socket
        self._identify = identify_program
        self._timeout = io_timeout
        self._lock = asyncio.Lock()
        self._subscription = None

    async def _send(self, message):
        frame = encode_frame(message)
        async with self._lock, asyncio.timeout(self._timeout):
            self._writer.write(frame)
            await self._writer.drain()

    async def result(self, request_id, data):
        await self._send({"version": PROTOCOL_VERSION, "requestId": request_id, "result": data})

    async def error(self, request_id, code, message):
        await self._send(
            {
                "version": PROTOCOL_VERSION,
                "requestId": request_id,
                "error": {"code": code, "message": message},
            }
        )

    async def status(self):
        try:
            status = await machine_status(self._socket)
        except (OSError, ValueError, TimeoutError, asyncio.IncompleteReadError):
            raise FeedbackError(
                "controller_unavailable", "local controller status unavailable"
            ) from None
        status["transferId"] = self._identify(status.get("file"))
        return status

    async def subscribe(self, interval):
        await self.unsubscribe()
        self._subscription = asyncio.create_task(self._publish(interval))

    async def _publish(self, interval):
        try:
            while True:
                event = {"version": PROTOCOL_VERSION, "event": "machine.status"}
                try:
                    event["data"] = await self.status()
                except FeedbackError as error:
                    event["error"] = {"code": error.code, "message": str(error)}
                await self._send(event)
                await asyncio.sleep(interval)
        except (ConnectionError, OSError, TimeoutError, ValueError):
            # A stalled subscriber cannot keep a live upload session indefinitely.
            self._writer.close()

    async def unsubscribe(self):
        if self._subscription is not None:
            self._subscription.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._subscription
            self._subscription = None

    async def close(self):
        await self.unsubscribe()
