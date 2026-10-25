"""Graphical-session bootstrap for the installed systemd user unit."""

import json
import os
import select
import shutil
import signal
import subprocess
import time


def _start_status_page(stop_requested):
    command = shutil.which("betterlinuxcnc")
    if command is None:
        raise ValueError("专用状态页需要已安装的 betterlinuxcnc")
    process = subprocess.Popen(
        [command, "--kiosk-status"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        pending = b""
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and process.poll() is None and not stop_requested():
            readable, _, _ = select.select([process.stdout], [], [], 0.25)
            if not readable:
                continue
            chunk = os.read(process.stdout.fileno(), 4096)
            if not chunk:
                break
            pending += chunk
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if isinstance(record, dict) and record.get("kioskStatus") == "visible":
                    return process
            if len(pending) > 4096:
                break
        raise RuntimeError("专用状态页未能及时显示")
    except BaseException:
        _stop_status_page(process)
        raise


def _stop_status_page(process):
    if process is None:
        return
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    process.stdout.close()


def start_session(*, kiosk=False):
    command = shutil.which("systemctl")
    if command is None:
        raise ValueError("自动启动需要 systemd 用户服务；手动启动请使用 betterlinuxcnc-launch")
    variables = [
        key
        for key in (
            "DISPLAY",
            "WAYLAND_DISPLAY",
            "XAUTHORITY",
            "XDG_SESSION_TYPE",
            "DBUS_SESSION_BUS_ADDRESS",
        )
        if os.environ.get(key)
    ]
    if not any(key in variables for key in ("DISPLAY", "WAYLAND_DISPLAY")):
        raise ValueError("没有图形会话，不能启动 LinuxCNC DISPLAY")
    environment = dict(
        os.environ,
        BETTERCNC_KIOSK="1" if kiosk else "0",
        BETTERCNC_FULLSCREEN="1" if kiosk else "0",
    )
    variables.extend(("BETTERCNC_KIOSK", "BETTERCNC_FULLSCREEN"))
    subprocess.run([command, "--user", "daemon-reload"], check=True, timeout=10)
    subprocess.run(
        [command, "--user", "import-environment", *variables],
        env=environment,
        check=True,
        timeout=10,
    )
    subprocess.run(
        [command, "--user", "start", "betterlinuxcnc-launcher.service"], check=True, timeout=15
    )
    return 0


def run_kiosk_session():
    """Own the X11 session lifetime independently of the supervised machine stack."""
    if os.getuid() == 0:
        raise ValueError("专用图形会话必须由普通操作账户运行")
    if not os.environ.get("DISPLAY") or os.environ.get("XDG_SESSION_TYPE", "x11") != "x11":
        raise ValueError("专用图形会话需要 X11 DISPLAY")
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    previous = {
        signal.SIGINT: signal.signal(signal.SIGINT, signal.SIG_IGN),
        signal.SIGTERM: signal.signal(signal.SIGTERM, stop),
        signal.SIGHUP: signal.signal(signal.SIGHUP, stop),
    }
    status_page = None
    try:
        try:
            status_page = _start_status_page(lambda: stopping)
        except (subprocess.SubprocessError, OSError, ValueError, RuntimeError) as error:
            # A late status window must never map over the native machine UI.
            print(f"专用状态页不可用：{error}", flush=True)
        if stopping:
            return 0
        try:
            start_session(kiosk=True)
        except (subprocess.SubprocessError, OSError, ValueError) as error:
            print(f"CNC 启动失败，保留专用图形会话供维护处理：{error}", flush=True)
        # Never return to the display manager on service failure or an orderly
        # stop. In particular, exit 78 may leave a live core and GUI in place.
        # The maintenance account owns explicit session termination; this
        # container neither restarts the service nor sends machine commands.
        while not stopping:
            time.sleep(0.25)
        return 0
    finally:
        _stop_status_page(status_page)
        for sig, handler in previous.items():
            signal.signal(sig, handler)
