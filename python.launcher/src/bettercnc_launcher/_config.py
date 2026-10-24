"""Resolve one explicit machine configuration without rewriting INI or HAL."""

import configparser
import ipaddress
import json
import math
import os
import re
import shlex
import shutil
import ssl
import stat
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"重复配置项：{key}")
        result[key] = value
    return result


def _keys(value, allowed):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError(f"配置仅允许这些字段：{', '.join(allowed)}")


def _path(value, base):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("路径必须是非空字符串")
    path = Path(value).expanduser()
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def _positive(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 300:
        raise ValueError(f"{name} 必须在 0–300 秒之间")
    return float(value)


def _executable(name):
    result = shutil.which(name)
    if result is None:
        raise ValueError(f"缺少可执行程序：{name}")
    return result


def _private_file(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError(f"文件必须属于当前用户且禁止其他用户访问：{path}")
    return info


@dataclass(frozen=True)
class Config:
    ini: Path
    socket: Path
    state: Path
    startup_timeout: float
    shutdown_timeout: float
    service: tuple
    native: tuple
    cam: tuple | None
    cam_endpoint: tuple | None

    def plan(self):
        return {
            "ini": str(self.ini),
            "socket": str(self.socket),
            "logRoot": str(self.state),
            "commands": [
                list(command) for command in (self.service, self.native, self.cam) if command
            ],
        }


def load(path, ini_override=None):
    data = {}
    if path.exists():
        if path.stat().st_size > 65536:
            raise ValueError("启动配置超过 64 KiB")
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object)
    elif ini_override is None:
        raise ValueError(f"请提供 --ini 或创建启动配置：{path}")
    _keys(data, ("ini", "cam", "startup_timeout", "shutdown_timeout"))
    ini = _path(ini_override, Path.cwd()) if ini_override else _path(data.get("ini"), path.parent)
    if not ini.is_file():
        raise ValueError(f"INI 不存在：{ini}")
    # LinuxCNC permits repeated HALFILE keys and has its own complete INI parser.
    parser = configparser.ConfigParser(
        strict=False, interpolation=None, inline_comment_prefixes=("#", ";")
    )
    try:
        parser.read_string(ini.read_text(encoding="utf-8"))
    except configparser.Error as error:
        raise ValueError(f"INI 格式无效：{error}") from None
    display = shlex.split(parser.get("DISPLAY", "DISPLAY", fallback=""))
    if not display or display[0] != "betterlinuxcnc":
        raise ValueError(
            "统一入口要求 INI 的 [DISPLAY] DISPLAY = betterlinuxcnc；请先核对专属 POSTGUI_HALFILE"
        )
    if any(
        arg in ("--ini", "-ini", "--socket") or arg.startswith(("--ini=", "--socket="))
        for arg in display[1:]
    ):
        raise ValueError("INI 的 DISPLAY 不得覆盖启动器的 INI 或 socket")
    _executable("betterlinuxcnc")
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()) / "betterlinuxcnc"
    state = (
        Path(os.environ["BETTERCNC_LOG_ROOT"]).expanduser().resolve()
        if os.environ.get("BETTERCNC_LOG_ROOT")
        else path.parent / ".runtime" / "launcher"
    )
    service = [
        _executable("betterlinuxcnc-service"),
        "--socket",
        str(runtime / "control.sock"),
        "--ini",
        str(ini),
    ]
    native = (_executable("linuxcnc"), str(ini))
    cam, endpoint = None, None
    if data.get("cam") is not None:
        options = data["cam"]
        _keys(
            options, ("host", "port", "inbox", "token_file", "cert", "key", "auto_run", "discovery")
        )
        host = str(ipaddress.IPv4Address(options.get("host", "127.0.0.1")))
        port = options.get("port", 6522)
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("CAM port 必须在 1–65535 之间")
        inbox = _path(options.get("inbox"), path.parent)
        token = None
        if options.get("token_file") is not None:
            token = _path(options["token_file"], path.parent)
            token_source = Path(options["token_file"]).expanduser()
            if not token_source.is_absolute():
                token_source = path.parent / token_source
            if _private_file(token_source).st_size > 257 or not re.fullmatch(
                r"[A-Za-z0-9_-]{32,256}", token.read_text(encoding="ascii").strip()
            ):
                raise ValueError("CAM 令牌必须包含 32–256 个 URL-safe 字符")
        auto_run = options.get("auto_run", False)
        if type(auto_run) is not bool:
            raise ValueError("auto_run 必须是布尔值")
        args = [
            _executable("betterlinuxcnc-cam-link"),
            "--host",
            host,
            "--port",
            str(port),
            "--inbox",
            str(inbox),
            "--control-socket",
            str(runtime / "control.sock"),
        ]
        if token is not None:
            args += ["--token-file", str(token)]
        cert, key = options.get("cert"), options.get("key")
        if bool(cert) != bool(key) or (
            token is not None and not ipaddress.ip_address(host).is_loopback and not cert
        ):
            raise ValueError("局域网 CAM 服务必须配置 cert/key；两者必须同时提供")
        if cert:
            cert, key = _path(cert, path.parent), _path(key, path.parent)
            _private_file(key)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            args += ["--cert", str(cert), "--key", str(key)]
        if auto_run:
            args += ["--auto-run"]
            service += ["--cam-inbox", str(inbox)]
        discovery = options.get("discovery")
        if discovery is not None:
            _keys(discovery, ("device_id", "device_name", "address"))
            device_id = str(uuid.UUID(discovery.get("device_id", "")))
            name = discovery.get("device_name")
            if not isinstance(name, str) or not name.strip() or len(name) > 64:
                raise ValueError("发现设备名称必须为 1–64 个字符")
            address = str(ipaddress.IPv4Address(discovery.get("address", "255.255.255.255")))
            args += [
                "--discover",
                "--device-id",
                device_id,
                "--device-name",
                name,
                "--discovery-address",
                address,
                "--discovery-port",
                "8421",
            ]
        cam, endpoint = tuple(args), (host, port, str(inbox))
    return Config(
        ini,
        runtime / "control.sock",
        state,
        _positive(data.get("startup_timeout", 45), "startup_timeout"),
        _positive(data.get("shutdown_timeout", 15), "shutdown_timeout"),
        tuple(service),
        native,
        cam,
        endpoint,
    )
