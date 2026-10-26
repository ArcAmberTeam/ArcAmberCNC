"""Read-only v2 observer adapter. Never attaches an owner or issues commands."""

import json
import socket
import stat
import struct
import uuid


def _read(stream, size):
    data = bytearray()
    while len(data) < size:
        chunk = stream.recv(size - len(data))
        if not chunk:
            raise ValueError("控制服务提前关闭响应")
        data.extend(chunk)
    return bytes(data)


def status(path):
    if not stat.S_ISSOCK(path.lstat().st_mode):
        raise ValueError("控制服务端点不是 Unix socket")
    request_id = uuid.uuid4().hex
    request = json.dumps(
        {"version": 2, "request_id": request_id, "method": "machine.status", "params": {}}
    ).encode()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
        stream.settimeout(0.5)
        stream.connect(str(path))
        stream.sendall(struct.pack("!I", len(request)) + request)
        size = struct.unpack("!I", _read(stream, 4))[0]
        if not 0 < size <= 1024 * 1024:
            raise ValueError("控制服务响应长度无效")
        response = json.loads(_read(stream, size))
    if (
        not isinstance(response, dict)
        or response.get("version") != 2
        or response.get("request_id") != request_id
        or "error" in response
    ):
        raise ValueError("控制服务响应身份或状态无效")
    result = response.get("result")
    if not isinstance(result, dict) or type(result.get("connected")) is not bool:
        raise ValueError("控制服务未返回有效机床状态")
    return result


def quiescent(value):
    # Paused AUTO, pending jobs, queued motion and unreadable state cannot justify
    # shutting down the native process. This is an observer, never an interlock.
    return (
        value.get("connected") is True
        and value.get("programState") in ("idle", "off", "estop")
        and value.get("queueDepth") == 0
        and value.get("activeQueueDepth") == 0
        and not value.get("paused", False)
        and (value.get("job") or {}).get("state")
        not in ("accepted", "homing", "loading", "starting", "running", "unknown")
    )
