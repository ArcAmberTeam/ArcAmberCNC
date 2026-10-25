"""Durable at-most-once execution intent and immutable input snapshot for CAM jobs."""

import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path

ACTIVE = frozenset(("accepted", "loading", "starting", "running"))
_ID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\.(?:ngc|nc|gcode)")


def _sync(directory):
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _private(path, directory=False):
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("CAM 作业路径必须属于当前用户，目录为 0700、文件禁止其他用户访问")
    return info


class ReceivedPrograms:
    def __init__(self, directory):
        self.directory = Path(directory).absolute() if directory else None

    def _directory(self, transfer_id):
        if self.directory is None:
            raise ValueError("控制服务未配置 CAM 自动加工收件目录")
        if not isinstance(transfer_id, str) or not _ID.fullmatch(transfer_id):
            raise ValueError("transferId 必须是小写 UUID")
        _private(self.directory, True)
        directory = self.directory / transfer_id
        _private(directory, True)
        return directory

    def status(self, transfer_id):
        directory = self._directory(transfer_id)
        path = directory / "execution.json"
        if not path.exists() and not path.is_symlink():
            return None
        _private(path)
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict) or record.get("transferId") != transfer_id:
            raise ValueError("CAM 作业记录无效")
        if record.get("state") in ACTIVE:
            # A new Controller has no authority to resume another instance's work.
            record = {
                **record,
                "state": "unknown",
                "message": "服务会话已变化；结果未知，不会重放加工",
            }
        return record

    def reserve(self, transfer_id):
        directory = self._directory(transfer_id)
        _private(directory / "receipt.json")
        receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise ValueError("CAM 文件接收回执无效")
        name = receipt.get("filename")
        if (
            receipt.get("transferId") != transfer_id
            or receipt.get("state") != "received"
            or not isinstance(name, str)
            or not _NAME.fullmatch(name)
            or type(receipt.get("size")) is not int
            or not 0 < receipt["size"] <= 64 * 1024 * 1024
            or not isinstance(receipt.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", receipt["sha256"])
        ):
            raise ValueError("CAM 文件接收回执无效")
        source = directory / name
        _private(source)
        target = directory / ".execution.ngc"
        if len(os.fsencode(target)) > 254:
            raise ValueError("CAM 加工文件路径超过 LinuxCNC 上限")
        record = {
            "transferId": transfer_id,
            "filename": name,
            "path": str(target),
            "size": receipt["size"],
            "sha256": receipt["sha256"],
            "state": "accepted",
            "message": "自动加工请求已记录",
        }
        # Intent is durable before any NML command. Existing intent is never replaced.
        descriptor = os.open(
            directory / "execution.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        _sync(directory)
        try:
            digest = hashlib.sha256()
            size = 0
            source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
            target_fd = None
            try:
                target_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
                with (
                    os.fdopen(source_fd, "rb", closefd=False) as src,
                    os.fdopen(target_fd, "wb", closefd=False) as dst,
                ):
                    while chunk := src.read(1024 * 1024):
                        size += len(chunk)
                        if size > receipt["size"] or b"\0" in chunk:
                            raise ValueError("CAM 文件内容与接收回执不一致")
                        digest.update(chunk)
                        dst.write(chunk)
                    dst.flush()
                    os.fsync(dst.fileno())
            finally:
                os.close(source_fd)
                if target_fd is not None:
                    os.close(target_fd)
            if size != receipt["size"] or digest.hexdigest() != receipt["sha256"]:
                raise ValueError("CAM 文件摘要与接收回执不一致")
            _sync(directory)
        except Exception as error:
            self.update(record, "error", str(error))
            raise
        return record

    def update(self, record, state, message):
        directory = self._directory(record["transferId"])
        updated = {**record, "state": state, "message": message}
        descriptor, temporary = tempfile.mkstemp(prefix=".execution-", dir=directory)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(updated, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, directory / "execution.json")
            _sync(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        record.update(updated)
