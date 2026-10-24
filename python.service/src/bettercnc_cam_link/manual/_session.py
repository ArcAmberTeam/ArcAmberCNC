"""One TCP owner's jog lease; only the local Controller decides movement eligibility."""

import asyncio
import contextlib
import json
import math
import struct
import time
import uuid


class JogError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class JogSession:
    # Software deadlines, not a hard realtime stopping guarantee. The local
    # controller additionally owns its independent 600 ms continuous-jog lease.
    LEASE_SECONDS = 0.45

    def __init__(self, control_socket):
        self._socket = control_socket
        self._reader = self._writer = None
        self._jog_id = None
        self._used = set()
        self._deadline = 0
        self._watchdog = None

    async def _request(self, method, params):
        request_id = uuid.uuid4().hex
        body = json.dumps(
            {
                "version": 2,
                "request_id": request_id,
                "method": method,
                "params": params,
            }
        ).encode()
        async with asyncio.timeout(self.LEASE_SECONDS):
            self._writer.write(struct.pack("!I", len(body)) + body)
            await self._writer.drain()
            size = struct.unpack("!I", await self._reader.readexactly(4))[0]
            if not 0 < size <= 65536:
                raise JogError("invalid_response", "invalid local controller frame")
            reply = json.loads(await self._reader.readexactly(size))
        if (
            not isinstance(reply, dict)
            or reply.get("version") != 2
            or reply.get("request_id") != request_id
        ):
            raise JogError("invalid_response", "invalid local controller response")
        if "error" in reply:
            error = reply["error"]
            raise JogError(error.get("code", "jog_rejected"), error.get("message", "jog rejected"))
        if not isinstance(reply.get("result"), dict):
            raise JogError("invalid_response", "missing controller result")
        return reply["result"]

    async def _expire(self):
        while self._writer is not None:
            await asyncio.sleep(max(0, self._deadline - time.monotonic()))
            if time.monotonic() >= self._deadline:
                # Do not wait for an in-flight request or queued stop. EOF revokes
                # this owner and cancels its pending movement in the local service.
                self._writer.close()
                return

    async def request(self, method, params):
        if method not in ("jog.start", "jog.keepalive", "jog.stop"):
            raise JogError("unsupported_method", "unsupported manual control method")
        keys = {"jogId", "axis", "direction", "feedRate"} if method == "jog.start" else {"jogId"}
        if set(params) != keys:
            raise JogError("invalid_params", "invalid jog parameters")
        jog_id = params["jogId"]
        if not isinstance(jog_id, str):
            raise JogError("invalid_params", "jogId must be a UUID")
        try:
            if str(uuid.UUID(jog_id)) != jog_id:
                raise ValueError
        except ValueError:
            raise JogError("invalid_params", "jogId must be a canonical UUID") from None
        if method == "jog.stop":
            if self._jog_id == jog_id:
                await self.close()
            if len(self._used) < 2048:
                self._used.add(jog_id)
            return {"jogId": jog_id, "accepted": True}
        if method == "jog.keepalive":
            if self._jog_id != jog_id or self._writer is None or time.monotonic() >= self._deadline:
                await self.close()
                raise JogError("jog_expired", "jog ended; press again to start a new movement")
            try:
                await self._request("cam.jog.keepalive", {"jogId": jog_id})
                self._deadline = time.monotonic() + self.LEASE_SECONDS
            except (OSError, TimeoutError, asyncio.IncompleteReadError, ValueError):
                await self.close()
                raise JogError("jog_expired", "controller lease renewal failed") from None
            return {"jogId": jog_id, "accepted": True}
        if self._writer is not None or jog_id in self._used or len(self._used) >= 2048:
            raise JogError("jog_busy", "movement active or jogId already used")
        axis, direction, feed = params["axis"], params["direction"], params["feedRate"]
        if (
            axis not in ("X", "Y", "Z")
            or type(direction) is not int
            or direction not in (-1, 1)
            or type(feed) not in (int, float)
            or not math.isfinite(feed)
            or not 0 < feed <= 3000
        ):
            raise JogError("invalid_params", "invalid axis, direction or feed rate")
        self._used.add(jog_id)
        self._jog_id = jog_id
        self._deadline = time.monotonic() + self.LEASE_SECONDS
        try:
            async with asyncio.timeout(self.LEASE_SECONDS):
                self._reader, self._writer = await asyncio.open_unix_connection(str(self._socket))
            self._watchdog = asyncio.create_task(self._expire())
            result = await self._request("cam.jog.start", params)
            if result.get("accepted") is not True:
                raise JogError("jog_rejected", "controller rejected continuous jog")
            return {"jogId": jog_id, "accepted": True}
        except (OSError, TimeoutError, asyncio.IncompleteReadError, ValueError) as error:
            await self.close()
            if isinstance(error, JogError):
                raise
            raise JogError("controller_unavailable", "cannot establish continuous jog") from None

    async def close(self):
        watchdog, self._watchdog = self._watchdog, None
        writer, self._writer = self._writer, None
        self._jog_id = None
        # Close before any await, including cancellation of the watchdog, so a
        # server shutdown cannot interrupt cleanup while retaining ownership.
        if writer is not None:
            writer.close()
        if watchdog is not None:
            watchdog.cancel()
            await asyncio.gather(watchdog, return_exceptions=True)
        if writer is not None:
            with contextlib.suppress(ConnectionError, OSError):
                await writer.wait_closed()
