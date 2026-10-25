"""Exercise an actual DEB in the disposable GitHub CI container, never a machine."""

import grp
import hashlib
import json
import os
import pwd
import secrets
import stat
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


def run(*arguments, **kwargs):
    try:
        return subprocess.run(arguments, check=True, text=True, capture_output=True, **kwargs)
    except subprocess.CalledProcessError as error:
        print(error.stdout, file=sys.stderr)
        print(error.stderr, file=sys.stderr)
        raise


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def ownership(path, user, group, mode):
    value = Path(path).lstat()
    require(stat.S_ISDIR(value.st_mode), f"Not a real directory: {path}")
    require(value.st_uid == pwd.getpwnam(user).pw_uid, f"Unexpected owner: {path}")
    require(value.st_gid == grp.getgrnam(group).gr_gid, f"Unexpected group: {path}")
    require(stat.S_IMODE(value.st_mode) == mode, f"Unexpected permissions: {path}")


def accounts_and_paths():
    operator = pwd.getpwnam("linuxcnc")
    maintenance = pwd.getpwnam("cnc-maint")
    require(operator.pw_uid >= 1000 and maintenance.pw_uid >= 1000, "Invalid account UID")
    require(operator.pw_dir == "/var/lib/betterlinuxcnc/home", "Invalid operator HOME")
    require(maintenance.pw_dir == "/var/lib/betterlinuxcnc/maintenance", "Invalid maintenance HOME")
    for account in (operator, maintenance):
        names = {grp.getgrgid(gid).gr_name for gid in os.getgrouplist(account.pw_name, account.pw_gid)}
        require(not names & {"sudo", "adm", "disk", "root"}, "Privileged account group")
        require("cnc-logs" in names, "Missing read-only log group")
    for path in ("/etc/betterlinuxcnc", "/var/lib/betterlinuxcnc", "/var/cache/betterlinuxcnc", "/var/log/betterlinuxcnc"):
        ownership(path, "root", "root", 0o755)
    for child in ("home", "programs", "inbox", "machine"):
        ownership(f"/var/lib/betterlinuxcnc/{child}", "linuxcnc", "linuxcnc", 0o700)
    ownership("/var/cache/betterlinuxcnc/user", "linuxcnc", "linuxcnc", 0o700)
    ownership("/var/cache/betterlinuxcnc/update", "root", "root", 0o700)
    ownership("/var/lib/betterlinuxcnc/update", "root", "root", 0o755)
    ownership("/var/lib/betterlinuxcnc/maintenance", "root", "cnc-maint", 0o750)
    ownership("/var/log/betterlinuxcnc/launcher", "linuxcnc", "cnc-logs", 0o2750)
    return operator.pw_uid, maintenance.pw_uid


def password_digest():
    # Compare without exposing either a credential or its digest in CI output.
    value = next(line for line in Path("/etc/shadow").read_bytes().splitlines() if line.startswith(b"cnc-maint:"))
    return hashlib.sha256(value).digest()


def main():
    require(os.environ.get("GITHUB_ACTIONS") == "true" and os.geteuid() == 0, "GitHub CI container required")
    package, source = map(Path, sys.argv[1:])
    version = tomllib.loads((source / "app/desktop/pyproject.toml").read_text())["project"]["version"]
    fields = {field: run("dpkg-deb", "--field", str(package), field).stdout.strip() for field in ("Package", "Version", "Architecture")}
    require(fields == {"Package": "betterlinuxcnc-qt", "Version": version, "Architecture": "amd64"}, "Incorrect package metadata")
    require(package.name == f"betterlinuxcnc-qt_{version}_amd64.deb", "Incorrect package filename")
    with tempfile.TemporaryDirectory() as temporary:
        control = Path(temporary)
        run("dpkg-deb", "--control", str(package), str(control))
        require({item.name for item in control.iterdir()} <= {"control", "md5sums", "conffiles", "postinst"}, "Unexpected control file")
        require((control / "postinst").read_bytes() == (source / "tools/appliance/packaging/postinst").read_bytes(), "Unexpected postinst bytes")
        require(stat.S_IMODE((control / "postinst").stat().st_mode) == 0o755, "postinst must be executable")
    run("apt-get", "install", "-y", "--no-install-recommends", str(package))
    identities = accounts_and_paths()
    require(not Path("/etc/betterlinuxcnc/launcher.json").exists(), "Package imported a machine configuration")
    require(not Path("/etc/lightdm/lightdm.conf.d/90-betterlinuxcnc.conf").exists(), "Package activated display policy")
    require("ForceCommand /usr/bin/python3 -I /usr/lib/betterlinuxcnc" not in Path("/etc/ssh/sshd_config").read_text(), "Package activated SSH policy")
    for executable in ("betterlinuxcnc-cam-link", "betterlinuxcnc-updater"):
        require(Path("/usr/bin", executable).read_bytes().startswith(b"\x7fELF"), "Expected a real Linux Rust binary")
        run(f"/usr/bin/{executable}", "--help")
    installed_version = run("/usr/bin/python3", "-c", "import sys; sys.path.insert(0, '/usr/lib/betterlinuxcnc/python'); from bettercnc import __version__; print(__version__)").stdout.strip()
    require(installed_version == version, "Installed application version mismatch")

    # Exercise upgrade preservation with private, synthetic data, never machine commands.
    fixtures = {
        "/etc/betterlinuxcnc/launcher.json": b'{"ciFixture":true}\n',
        "/var/lib/betterlinuxcnc/programs/retain.ngc": b"; retained CI program\n",
        "/var/lib/betterlinuxcnc/inbox/retain.ngc": b"; retained CI inbox\n",
        "/var/lib/betterlinuxcnc/machine/tool.tbl": b"; retained CI tool data\n",
        "/var/log/betterlinuxcnc/launcher/retain.log": b"retained CI log\n",
    }
    for name, content in fixtures.items():
        Path(name).write_bytes(content)
    updater = Path("/etc/betterlinuxcnc/updater.json")
    fixtures[str(updater)] = updater.read_bytes() + b"\n"
    updater.write_bytes(fixtures[str(updater)])
    run("/usr/sbin/betterlinuxcnc-appliance", "set-maintenance-password", input=secrets.token_urlsafe(32) + "\n")
    password = password_digest()
    policies = json.loads(run("/usr/sbin/betterlinuxcnc-appliance", "plan").stdout)["policyFiles"]
    previous = {name: Path(name).read_bytes() if Path(name).is_file() else None for name in policies}
    run("dpkg", "--force-confold", "--install", str(package))
    require(accounts_and_paths() == identities, "Repeated install changed account identities")
    require(password_digest() == password, "Repeated install changed maintenance credentials")
    for name, content in fixtures.items():
        require(Path(name).read_bytes() == content, f"Repeated install changed persistent data: {name}")
    for name, content in previous.items():
        require((Path(name).read_bytes() if Path(name).is_file() else None) == content, f"Repeated install changed login policy: {name}")

    # Explicit activation is tested only here, in a container with no init or machine.
    run("ssh-keygen", "-A")
    Path("/run/sshd").mkdir(exist_ok=True)
    run("/usr/sbin/betterlinuxcnc-appliance", "activate")
    run("/usr/sbin/sshd", "-t")
    run("/usr/sbin/visudo", "-c")
    effective = run("/usr/sbin/sshd", "-T", "-C", "user=cnc-maint,host=localhost,addr=127.0.0.1").stdout
    for setting in ("allowusers cnc-maint", "permitrootlogin no", "permittty no", "disableforwarding yes", "forcecommand /usr/bin/python3 -I /usr/lib/betterlinuxcnc/appliance/maintenance.py"):
        require(setting in effective.splitlines(), f"Missing effective SSH restriction: {setting}")
    for account in ("linuxcnc", "cnc-maint"):
        result = subprocess.run(["sudo", "-n", "-l", "-U", account], capture_output=True, text=True)
        require(result.returncode != 0, f"Unexpected sudo grant: {account}")
    print("DEB metadata, Rust binaries, first/repeated provisioning, data retention and effective SSH/sudo policy passed")


if __name__ == "__main__":
    main()
