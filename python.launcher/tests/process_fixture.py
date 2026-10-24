"""Executable process boundary fixtures; never loads LinuxCNC, HAL or Qt."""

import json
import os
import signal
import socket
import struct
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(os.environ["FIXTURE_ROOT"])
ROLE = Path(sys.argv[0]).name
STOP = threading.Event()


def event(kind, **values):
    data = json.dumps({"role": ROLE, "event": kind, "pid": os.getpid(), **values}) + "\n"
    descriptor = os.open(ROOT / "events", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(descriptor, data.encode())
    finally:
        os.close(descriptor)


def stop(*_):
    event("stop")
    STOP.set()


def argument(name):
    return sys.argv[sys.argv.index(name) + 1]


def exact(stream, count):
    result = b""
    while len(result) < count:
        part = stream.recv(count - len(result))
        if not part:
            raise EOFError
        result += part
    return result


def controller():
    path = Path(argument("--socket"))
    if os.environ.get("FIXTURE_SERVICE_FAIL"):
        return 7
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(path))
        path.chmod(0o600)
        server.listen()
        server.settimeout(0.1)
        try:
            while not STOP.is_set():
                try:
                    stream, _ = server.accept()
                except TimeoutError:
                    continue
                with stream:
                    try:
                        stream.settimeout(1)
                        size = struct.unpack("!I", exact(stream, 4))[0]
                        request = json.loads(exact(stream, size))
                        event("request", method=request["method"])
                        if request["method"] != "machine.status":
                            raise AssertionError("launcher must be a read-only observer")
                        state = json.loads((ROOT / "machine.json").read_text())
                        state["connected"] = (ROOT / "native-ready").exists()
                        response = {
                            "version": 2,
                            "request_id": request["request_id"],
                            "result": state,
                        }
                        if (ROOT / "wrong-identity").exists():
                            response["request_id"] = "wrong"
                        body = json.dumps(response).encode()
                        framed = struct.pack("!I", len(body)) + body
                        # Exercise fragmented public protocol reads.
                        stream.sendall(framed[:2])
                        stream.sendall(framed[2:])
                    except (EOFError, BrokenPipeError, ConnectionResetError):
                        pass
        finally:
            path.unlink(missing_ok=True)
    return 0


def native():
    delay = float(os.environ.get("FIXTURE_NATIVE_DELAY", "0"))
    STOP.wait(delay)
    if STOP.is_set():
        return 0
    (ROOT / "native-ready").touch()
    display = subprocess.Popen(["betterlinuxcnc", "-ini", sys.argv[1]], stdin=subprocess.DEVNULL)
    while not STOP.wait(0.05) and not (ROOT / "quit-native").exists():
        pass
    (ROOT / "native-ready").unlink(missing_ok=True)
    display.terminate()
    display.wait(timeout=3)
    event("native-cleanup")
    return 0


def cam():
    if not (ROOT / "native-ready").exists():
        raise AssertionError("CAM started before native readiness")
    if os.environ.get("FIXTURE_CAM_FAIL"):
        return 9
    print(
        json.dumps(
            {
                "host": argument("--host"),
                "port": int(argument("--port")),
                "inbox": argument("--inbox"),
            }
        ),
        flush=True,
    )
    while not STOP.wait(0.05):
        if (ROOT / "fail-cam").exists():
            return 9
    return 0


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    event(
        "start",
        argv=sys.argv[1:],
        socket=os.environ.get("BETTERCNC_SOCKET"),
        managed=os.environ.get("BETTERCNC_MANAGED"),
    )
    if ROLE == "betterlinuxcnc-service":
        return controller()
    if ROLE == "linuxcnc":
        return native()
    if ROLE == "betterlinuxcnc-cam-link":
        return cam()
    STOP.wait()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        event("exit")
