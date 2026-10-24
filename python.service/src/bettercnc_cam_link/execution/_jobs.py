"""Network-to-local job adapter; no LinuxCNC, UI or controller implementation imports."""

import asyncio
import contextlib
import json
import struct
import uuid


class ExecutionError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class ExecutionGateway:
    def __init__(self, control_socket):
        self._socket = control_socket

    async def request(self, method, transfer_id):
        writer = None
        try:
            async with asyncio.timeout(10):
                reader, writer = await asyncio.open_unix_connection(str(self._socket), limit=65536)
                request_id = uuid.uuid4().hex
                body = json.dumps(
                    {
                        "version": 2,
                        "request_id": request_id,
                        "method": "cam.job." + method,
                        "params": {"transferId": transfer_id},
                    }
                ).encode()
                writer.write(struct.pack("!I", len(body)) + body)
                await writer.drain()
                size = struct.unpack("!I", await reader.readexactly(4))[0]
                if not 0 < size <= 65536:
                    raise ValueError("invalid execution response frame")
                result = json.loads(await reader.readexactly(size))
                if (
                    not isinstance(result, dict)
                    or result.get("version") != 2
                    or result.get("request_id") != request_id
                ):
                    raise ValueError("invalid execution response")
                if "error" in result:
                    error = result["error"]
                    raise ExecutionError(
                        error.get("code", "job_rejected"),
                        error.get("message", "controller rejected job"),
                    )
                if not isinstance(result.get("result"), dict) or "job" not in result["result"]:
                    raise ValueError("invalid execution result")
                return result["result"]["job"]
        except (OSError, TimeoutError, asyncio.IncompleteReadError, ValueError) as error:
            if isinstance(error, ExecutionError):
                raise
            raise ExecutionError(
                "controller_unavailable",
                "自动加工请求结果未知；请检查机床端作业状态，禁止自动重试启动",
            ) from None
        finally:
            if writer is not None:
                writer.close()
                with contextlib.suppress(ConnectionError, OSError):
                    await writer.wait_closed()
