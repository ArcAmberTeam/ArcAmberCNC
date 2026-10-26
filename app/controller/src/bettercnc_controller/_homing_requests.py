"""Durable standalone CAM homing intents, independent of program transfers."""

import json
import os
import tempfile
from pathlib import Path

from ._received import ACTIVE, _ID, _private, _sync


class HomingRequests:
    def __init__(self, inbox):
        self.inbox = Path(inbox).absolute() if inbox else None

    def _path(self, operation_id):
        if self.inbox is None:
            raise ValueError("控制服务未配置 CAM 收件目录")
        if not isinstance(operation_id, str) or not _ID.fullmatch(operation_id):
            raise ValueError("operationId 必须是小写 UUID")
        _private(self.inbox, True)
        directory = self.inbox / ".homing"
        directory.mkdir(mode=0o700, exist_ok=True)
        _private(directory, True)
        _sync(self.inbox)
        return directory / (operation_id + ".json")

    def status(self, operation_id):
        path = self._path(operation_id)
        if not path.exists() and not path.is_symlink():
            return None
        _private(path)
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict) or record.get("operationId") != operation_id:
            raise ValueError("CAM 回零记录无效")
        if record.get("state") in ACTIVE:
            record = {**record, "state": "unknown", "message": "服务会话已变化；不会重放回零"}
        return record

    def reserve(self, operation_id):
        path = self._path(operation_id)
        record = {
            "operationId": operation_id,
            "kind": "homing",
            "state": "accepted",
            "message": "回零请求已记录",
        }
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        _sync(path.parent)
        return record

    def update(self, record, state, message):
        path = self._path(record["operationId"])
        updated = {**record, "state": state, "message": message}
        descriptor, temporary = tempfile.mkstemp(prefix=".homing-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(updated, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            _sync(path.parent)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        record.update(updated)
