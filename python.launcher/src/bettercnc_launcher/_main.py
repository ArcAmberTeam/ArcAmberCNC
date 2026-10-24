"""Explicit CLI. Defaults belong to the running project, never the home config."""

import argparse
import json
import os
import subprocess
from pathlib import Path

from ._autostart import start_session
from ._config import load
from ._supervisor import RecoveryBlocked, Runtime


def main(argv=None):
    parser = argparse.ArgumentParser(description="BetterLinuxCNC 标准库启动编排")
    parser.add_argument("--config", type=Path, help="项目启动配置，默认 ./launcher.json")
    parser.add_argument("--ini", help="覆盖本次启动的 INI 路径")
    parser.add_argument("--check", action="store_true", help="只校验配置和依赖，不启动进程")
    parser.add_argument("--once", action="store_true", help="单次运行，不自动拉起退出的模块")
    parser.add_argument("--session-start", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.session_start:
            return start_session()
        if args.config is not None and not args.config.expanduser().is_file():
            raise ValueError(f"启动配置不存在：{args.config}")
        config = load(
            (args.config or Path.cwd() / "launcher.json").expanduser().resolve(), args.ini
        )
        if args.check:
            print(json.dumps(config.plan(), ensure_ascii=False, indent=2))
            return 0
        os.umask(0o077)
        return Runtime(config, keep_alive=not args.once).run()
    except RecoveryBlocked as error:
        print(f"无法启动：{error}")
        return 78
    except (subprocess.SubprocessError, OSError, ValueError) as error:
        parser.exit(1, f"无法启动：{error}\n")
