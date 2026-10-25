"""Root-only account provisioning and explicit machine/policy administration."""

import argparse
import json
import os
import pwd
import subprocess
import sys
from pathlib import Path

# -I rejects caller-controlled Python paths; only installed sibling modules load.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _accounts
import _machine
import _policy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser(
        "plan", help="Show fixed paths and account policy without changing the host"
    )
    commands.add_parser(
        "provision",
        help="Idempotently create dedicated accounts and system data directories",
    )
    stage = commands.add_parser(
        "stage", help="Preview a machine import in a new staging directory"
    )
    stage.add_argument("--source-config", required=True, type=Path)
    stage.add_argument("--destination", required=True, type=Path)
    prepare = commands.add_parser(
        "prepare", help="Create accounts and copy an existing machine profile"
    )
    prepare.add_argument("--source-config", required=True, type=Path)
    commands.add_parser(
        "set-maintenance-password", help="Read one initial password from stdin"
    )
    commands.add_parser(
        "activate", help="Install fixed login policies; does not restart the display"
    )
    args = parser.parse_args()
    if args.action == "plan":
        print(
            json.dumps(
                {
                    "operator": _accounts.OPERATOR,
                    "maintenance": _accounts.MAINTENANCE,
                    "operatorHome": str(_accounts.HOME),
                    "config": str(_machine.CONFIG),
                    "data": str(_machine.DATA),
                    "policyFiles": list(_policy.POLICIES),
                    "passwordInPackage": False,
                    "automaticActivation": False,
                    "automaticAccountProvisioning": True,
                },
                indent=2,
            )
        )
        return 0
    if args.action == "stage":
        root = _machine.stage(args.source_config, args.destination)
        print(f"Migration staged without changing host policy: {root}")
        return 0
    if sys.platform != "linux" or os.geteuid() != 0:
        raise ValueError("Host provisioning requires a Linux root maintenance session")
    if args.action == "provision":
        _accounts.provision()
        if Path("/run/systemd/system").is_dir():
            _accounts.run("/usr/bin/systemctl", "daemon-reload")
        print("Provisioned dedicated accounts and system data directories")
    elif args.action == "prepare":
        _accounts.prepare()
        account = pwd.getpwnam(_accounts.OPERATOR)
        _policy.write(
            "/etc/betterlinuxcnc/updater.json",
            json.dumps(
                {"user": "linuxcnc", "config": "/etc/betterlinuxcnc/launcher.json"}
            )
            + "\n",
        )
        _machine.migrate(args.source_config, owner=(account.pw_uid, account.pw_gid))
        print("Prepared fixed appliance paths; original machine files are preserved")
    elif args.action == "set-maintenance-password":
        _accounts.password(sys.stdin.readline(258).rstrip("\n"))
        print("Maintenance password configured; future updates do not reset it")
    elif args.action == "activate":
        for name in ("linuxcnc", "cnc-maint"):
            pwd.getpwnam(name)
        if not Path("/etc/betterlinuxcnc/launcher.json").is_file():
            raise ValueError("Prepare and verify the machine configuration first")
        if not Path("/usr/share/xsessions/betterlinuxcnc-kiosk.desktop").is_file():
            raise ValueError(
                "The installed package does not provide the dedicated session"
            )
        recovery = _policy.install()
        print(f"Login policy installed; recovery manifest: {recovery}/policies.json")
        print(
            "Validate a new maintenance SSH connection before retiring the current session"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"Appliance provisioning refused: {error}", file=sys.stderr)
        raise SystemExit(1) from None
