"""Graphical-session bootstrap for the installed systemd user unit."""

import os
import shutil
import subprocess


def start_session():
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
    subprocess.run([command, "--user", "daemon-reload"], check=True, timeout=10)
    subprocess.run([command, "--user", "import-environment", *variables], check=True, timeout=10)
    subprocess.run(
        [command, "--user", "start", "betterlinuxcnc-launcher.service"], check=True, timeout=15
    )
    return 0
