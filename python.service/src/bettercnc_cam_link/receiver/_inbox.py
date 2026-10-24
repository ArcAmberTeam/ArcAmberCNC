"""Validate and atomically publish received programs, independently of transport."""

import codecs
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from pathlib import Path

ID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
FILENAME = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\.(?:ngc|nc|gcode)"


class ReceiveError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _transfer_id(value):
    if not isinstance(value, str) or not re.fullmatch(ID, value):
        raise ReceiveError("invalid_transfer_id", "transferId must be a lowercase UUID")
    return value


def _sync(directory):
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class ProgramInbox:
    """Own the receive directory, metadata validation and receipt lookup."""

    def __init__(self, directory, *, max_bytes=64 * 1024 * 1024):
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        path = Path(directory).absolute()
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = path.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            raise ValueError("inbox must be a user-owned directory with mode 0700")
        self.directory = path.resolve()
        self._max_bytes = max_bytes

    def begin(self, *, transfer_id, filename, size, sha256):
        _transfer_id(transfer_id)
        if not isinstance(filename, str) or not re.fullmatch(FILENAME, filename):
            raise ReceiveError(
                "invalid_filename", "filename must be a plain .ngc, .nc or .gcode name"
            )
        if type(size) is not int or not 0 < size <= self._max_bytes:
            raise ReceiveError("invalid_size", "program size must be positive and within the limit")
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ReceiveError("invalid_sha256", "sha256 must contain 64 lowercase hex digits")
        return ProgramUpload(self, transfer_id, filename, size, sha256)

    def receipt(self, transfer_id):
        directory = self.directory / _transfer_id(transfer_id)
        path = directory / "receipt.json"
        if directory.is_symlink() or path.is_symlink():
            raise ReceiveError("invalid_receipt", "receipt paths cannot be symlinks")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ReceiveError(
                "unknown_transfer", "no complete program has this transferId"
            ) from None

        except (ValueError, UnicodeError):
            raise ReceiveError("invalid_receipt", "stored receipt is not valid JSON") from None

    def identify(self, filename):
        """Correlate a machine file path with a receipt, without claiming job completion."""
        if not isinstance(filename, str) or not filename:
            return None
        try:
            path = Path(filename).resolve()
            if path.parent.parent == self.directory:
                data = self.receipt(path.parent.name)
                if path.name == data["filename"]:
                    return data["transferId"]
        except (OSError, ValueError, KeyError):
            pass
        return None


class ProgramUpload:
    """One sequential upload; close aborts and removes unpublished bytes."""

    def __init__(self, inbox, transfer_id, filename, size, digest):
        self._inbox = inbox
        self._directory = Path(tempfile.mkdtemp(prefix=".receiving-", dir=inbox.directory))
        self._data = {
            "transferId": transfer_id,
            "filename": filename,
            "size": size,
            "sha256": digest,
            "state": "received",
        }
        self._stream = None
        self.offset = 0
        self._hash = hashlib.sha256()
        self._decoder = codecs.getincrementaldecoder("utf-8")()
        try:
            self._stream = (self._directory / filename).open("xb")
            os.fchmod(self._stream.fileno(), 0o600)
        except OSError:
            self.close()
            raise

    def write(self, offset, chunk):
        if self._stream is None or self._stream.closed:
            raise ReceiveError("upload_closed", "upload is closed")
        if type(offset) is not int or offset != self.offset:
            raise ReceiveError("offset_mismatch", "chunk offset must match nextOffset")
        if (
            not isinstance(chunk, bytes)
            or not chunk
            or self.offset + len(chunk) > self._data["size"]
        ):
            raise ReceiveError("invalid_chunk_size", "chunk exceeds the declared program size")
        if b"\x00" in chunk:
            raise ReceiveError("invalid_program", "program must not contain NUL bytes")
        try:
            self._decoder.decode(chunk)
        except UnicodeError:
            raise ReceiveError("invalid_program", "program must be UTF-8") from None
        self._stream.write(chunk)
        self._hash.update(chunk)
        self.offset += len(chunk)

    def finish(self):
        if self._stream is None or self._stream.closed:
            raise ReceiveError("upload_closed", "upload is closed")
        if self.offset != self._data["size"]:
            raise ReceiveError("incomplete_program", "received size differs from declared size")
        try:
            self._decoder.decode(b"", final=True)
        except UnicodeError:
            raise ReceiveError("invalid_program", "program ends inside a UTF-8 character") from None
        if self._hash.hexdigest() != self._data["sha256"]:
            raise ReceiveError("sha256_mismatch", "SHA-256 mismatch")
        self._stream.flush()
        os.fsync(self._stream.fileno())
        self._stream.close()
        with (self._directory / "receipt.json").open("x", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(self._data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        _sync(self._directory)
        target = self._inbox.directory / self._data["transferId"]
        duplicate = target.exists() or target.is_symlink()
        # Publication has no await: clients cannot replace an existing receipt.
        if duplicate:
            if self._inbox.receipt(self._data["transferId"]) != self._data:
                raise ReceiveError(
                    "transfer_id_conflict", "transferId already has different content"
                )
        else:
            os.rename(self._directory, target)
            _sync(self._inbox.directory)
        self.close()
        return {**self._data, "duplicate": duplicate}

    def close(self):
        if self._stream is not None:
            self._stream.close()
        shutil.rmtree(self._directory, ignore_errors=True)
