"""Compose the TCP protocol, program receiver and outbound feedback capabilities."""

import argparse
import asyncio
import contextlib
import hmac
import json
import math
import os
import re
import signal
import socket
import ssl
import stat
from pathlib import Path

from ._discovery import DiscoveryOptions, run_discovery
from .execution import ExecutionError, ExecutionGateway
from .feedback import FeedbackChannel, FeedbackError
from .manual import JogError, JogSession
from .protocol import MAX_FRAME_BYTES, ProtocolError, decode_chunk, read_request
from .receiver import ProgramInbox, ReceiveError


def _params(params, *keys):
    if set(params) != set(keys):
        raise ProtocolError("invalid_params", "parameters do not match this method")


async def serve(
    inbox,
    *,
    token,
    control_socket,
    host="127.0.0.1",
    port=6522,
    max_bytes=64 * 1024 * 1024,
    io_timeout=10.0,
    idle_timeout=60.0,
    ssl_context=None,
    stop_event=None,
    sock=None,
    discovery=None,
    auto_run=False,
):
    """Serve the authenticated CAM Link v2 TCP protocol on a persistent connection.

    protocol owns framing, receiver owns staged program files, and feedback owns
    all replies and machine-status events. Optional execution delegates jobs to the
    local Controller; this process never opens LinuxCNC command channels.
    discovery optionally enables machine announcements and UDP discovery handshakes.
    An optional bound socket supports host activation and embedding.
    """
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token):
        raise ValueError("token must contain 32 to 256 URL-safe characters")
    if any(not math.isfinite(value) or value <= 0 for value in (io_timeout, idle_timeout)):
        raise ValueError("timeouts must be positive and finite")
    if discovery is not None:
        if not isinstance(discovery, DiscoveryOptions):
            raise ValueError("discovery must be DiscoveryOptions or None")
        discovery.validate()
    if type(auto_run) is not bool:
        raise ValueError("auto_run must be boolean")
    programs = ProgramInbox(inbox, max_bytes=max_bytes)
    execution = ExecutionGateway(control_socket)
    clients = set()

    async def handle(reader, writer):
        task = asyncio.current_task()
        admitted = len(clients) < 4
        if admitted:
            clients.add(task)
        channel = FeedbackChannel(
            writer,
            control_socket=control_socket,
            identify_program=programs.identify,
            io_timeout=io_timeout,
        )
        jog = JogSession(control_socket)
        upload = None
        authenticated = False
        ids = set()

        async def route(request):
            nonlocal upload
            method, params = request.method, request.params
            if method in ("jog.start", "jog.keepalive", "jog.stop"):
                return await jog.request(method, params)
            if method == "ping":
                _params(params)
                return {"alive": True}
            if method == "upload.begin":
                _params(params, "transferId", "filename", "size", "sha256")
                if upload is not None:
                    raise ReceiveError("upload_in_progress", "finish or abort the current upload")
                upload = programs.begin(
                    transfer_id=params["transferId"],
                    filename=params["filename"],
                    size=params["size"],
                    sha256=params["sha256"],
                )
                return {"state": "receiving", "nextOffset": 0}
            if method in ("upload.chunk", "upload.finish"):
                if upload is None:
                    raise ReceiveError("no_upload", "begin an upload first")
                if method == "upload.chunk":
                    _params(params, "offset", "data")
                    upload.write(params["offset"], decode_chunk(params["data"]))
                    return {"nextOffset": upload.offset}
                _params(params)
                result = upload.finish()
                upload = None
                if auto_run and not result["duplicate"]:
                    try:
                        result["job"] = await execution.request("start", result["transferId"])
                    except ExecutionError as error:
                        result["job"] = {
                            "transferId": result["transferId"],
                            "state": "unknown"
                            if error.code == "controller_unavailable"
                            else "error",
                            "message": str(error),
                        }
                elif auto_run:
                    result["job"] = await execution.request("status", result["transferId"])
                return result
            if method == "upload.abort":
                _params(params)
                if upload is not None:
                    upload.close()
                    upload = None
                return {"aborted": True}
            if method == "upload.receipt":
                _params(params, "transferId")
                result = programs.receipt(params["transferId"])
                if auto_run:
                    result["job"] = await execution.request("status", params["transferId"])
                return result
            if method in ("job.start", "job.status"):
                _params(params, "transferId")
                if not auto_run:
                    raise ExecutionError("auto_run_disabled", "CAM auto execution is disabled")
                programs.receipt(params["transferId"])
                return {"job": await execution.request(method.split(".")[1], params["transferId"])}
            if method == "status.get":
                _params(params)
                return await channel.status()
            if method == "status.subscribe":
                _params(params, "interval")
                interval = params["interval"]
                if type(interval) not in (int, float) or not 1 <= interval <= 60:
                    raise ProtocolError("invalid_params", "interval must be 1 to 60 seconds")
                return {"subscribed": True, "interval": interval}
            if method == "status.unsubscribe":
                _params(params)
                await channel.unsubscribe()
                return {"subscribed": False}
            raise ProtocolError("unsupported_method", "unsupported CAM Link method")

        try:
            if not admitted:
                return
            while True:
                try:
                    request = await read_request(
                        reader,
                        idle_timeout=idle_timeout if authenticated else io_timeout,
                        io_timeout=io_timeout,
                    )
                except ProtocolError as error:
                    await channel.error(error.request_id, error.code, str(error))
                    break
                if request.request_id in ids:
                    await channel.error(
                        request.request_id, "duplicate_request", "requestId was used"
                    )
                    continue
                if len(ids) >= 100000:
                    await channel.error(
                        request.request_id, "session_limit", "reconnect to continue"
                    )
                    break
                ids.add(request.request_id)
                if not authenticated:
                    valid = (
                        request.method == "session.auth"
                        and set(request.params) == {"token"}
                        and isinstance(request.params["token"], str)
                        and request.params["token"].isascii()
                        and hmac.compare_digest(request.params["token"], token)
                    )
                    if not valid:
                        await channel.error(
                            request.request_id, "unauthorized", "authenticate first"
                        )
                        break
                    authenticated = True
                    await channel.result(request.request_id, {"authenticated": True})
                    continue
                try:
                    result = await route(request)
                except (
                    ProtocolError,
                    ReceiveError,
                    FeedbackError,
                    ExecutionError,
                    JogError,
                ) as error:
                    if request.method in ("upload.chunk", "upload.finish") and upload is not None:
                        upload.close()
                        upload = None
                    await channel.error(request.request_id, error.code, str(error))
                except OSError:
                    if upload is not None:
                        upload.close()
                        upload = None
                    await channel.error(
                        request.request_id, "storage_unavailable", "inbox I/O failed"
                    )
                else:
                    await channel.result(request.request_id, result)
                    if request.method == "status.subscribe":
                        await channel.subscribe(result["interval"])
        except (asyncio.IncompleteReadError, ConnectionError, OSError, TimeoutError):
            pass
        finally:
            await jog.close()
            await channel.close()
            if upload is not None:
                upload.close()
            clients.discard(task)
            writer.close()
            with contextlib.suppress(ConnectionError, OSError):
                await writer.wait_closed()

    stopped = stop_event if stop_event is not None else asyncio.Event()
    loop = asyncio.get_running_loop()
    signals = (signal.SIGINT, signal.SIGTERM) if stop_event is None else ()
    for sig in signals:
        loop.add_signal_handler(sig, stopped.set)
    server = None
    discovery_task = discovery_ready = stop_waiter = None
    try:
        address = {"sock": sock} if sock is not None else {"host": host, "port": port}
        tls = (
            {
                "ssl": ssl_context,
                "ssl_handshake_timeout": io_timeout,
                "ssl_shutdown_timeout": io_timeout,
            }
            if ssl_context
            else {}
        )
        server = await asyncio.start_server(handle, limit=MAX_FRAME_BYTES, **address, **tls)
        address = server.sockets[0].getsockname()
        if discovery is not None:
            ipv4 = [listener for listener in server.sockets if listener.family == socket.AF_INET]
            if len(ipv4) != 1:
                raise ValueError("discovery requires one IPv4 TCP listener")
            discovery_ready = loop.create_future()
            discovery_task = asyncio.create_task(
                run_discovery(
                    discovery,
                    tcp_address=ipv4[0].getsockname(),
                    tls=bool(ssl_context),
                    ready=discovery_ready,
                )
            )
            finished, _ = await asyncio.wait(
                (discovery_ready, discovery_task), return_when=asyncio.FIRST_COMPLETED
            )
            if discovery_task in finished:
                await discovery_task
        print(
            json.dumps({"host": address[0], "port": address[1], "inbox": str(programs.directory)}),
            flush=True,
        )
        if discovery_task is None:
            await stopped.wait()
        else:
            stop_waiter = asyncio.create_task(stopped.wait())
            finished, _ = await asyncio.wait(
                (stop_waiter, discovery_task), return_when=asyncio.FIRST_COMPLETED
            )
            if discovery_task in finished:
                await discovery_task
    finally:
        if server is not None:
            server.close()
        if discovery_ready is not None and not discovery_ready.done():
            discovery_ready.cancel()
        discovery_tasks = [task for task in (discovery_task, stop_waiter) if task is not None]
        for task in discovery_tasks:
            task.cancel()
        await asyncio.gather(*discovery_tasks, return_exceptions=True)
        pending = list(clients)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        if server is not None:
            await server.wait_closed()
        for sig in signals:
            loop.remove_signal_handler(sig)


def main():
    parser = argparse.ArgumentParser(description="CAM link TCP reception and machining feedback")
    parser.add_argument("--inbox", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--control-socket", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6522)
    parser.add_argument("--max-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--idle-timeout", type=float, default=60.0)
    parser.add_argument("--cert", type=Path)
    parser.add_argument("--key", type=Path)
    parser.add_argument(
        "--auto-run",
        action="store_true",
        help="submit newly received programs to the configured controller",
    )
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--device-id")
    parser.add_argument("--device-name", default=socket.gethostname()[:64])
    parser.add_argument("--discovery-address", default="255.255.255.255")
    parser.add_argument("--discovery-port", type=int, default=8421)
    parser.add_argument("--discovery-bind-port", type=int)
    parser.add_argument("--discovery-interval", type=float, default=3.0)
    args = parser.parse_args()
    try:
        if bool(args.cert) != bool(args.key):
            raise ValueError("--cert and --key must be supplied together")
        discovery = None
        if args.discover:
            if not args.device_id:
                raise ValueError("--discover requires a stable --device-id UUID")
            discovery = DiscoveryOptions(
                device_id=args.device_id,
                device_name=args.device_name,
                address=args.discovery_address,
                port=args.discovery_port,
                bind_port=args.discovery_bind_port,
                interval=args.discovery_interval,
            )
        info = args.token_file.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or info.st_size > 257
        ):
            raise ValueError("token file must be user-owned, mode 0600, and at most 257 bytes")
        token = args.token_file.read_text(encoding="ascii").strip()
        context = None
        if args.cert:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(args.cert, args.key)
        asyncio.run(
            serve(
                args.inbox,
                token=token,
                control_socket=args.control_socket,
                host=args.host,
                port=args.port,
                max_bytes=args.max_bytes,
                idle_timeout=args.idle_timeout,
                ssl_context=context,
                discovery=discovery,
                auto_run=args.auto_run,
            )
        )
    except (OSError, ValueError) as error:
        parser.exit(1, f"Cannot start CAM link service: {error}\n")
