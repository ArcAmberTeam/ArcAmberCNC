"""A noninteractive session background, observing only launcher state files."""

import json
import os
import re
import stat
import time

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtQuick import QQuickWindow

LOG_ROOT = "/var/log/betterlinuxcnc/launcher"
RUN_NAME = re.compile(r"[0-9]{8}-[0-9]{6}-[1-9][0-9]*")
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


class KioskStatus(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._started = time.monotonic()
        self._phase = "starting"
        self._window = None
        self._announced = False
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._refresh)
        self._refresh()
        self._timer.start()

    phase = Property(str, lambda self: self._phase, notify=changed)
    headline = Property(
        str,
        lambda self: "CNC 正在启动" if self._phase == "starting" else "CNC 尚未就绪",
        notify=changed,
    )
    message = Property(
        str,
        lambda self: (
            "正在等待控制服务和机床硬件就绪。"
            if self._phase == "starting"
            else "若持续显示此页，请联系维护人员查看启动日志并检查机床连接。"
        ),
        notify=changed,
    )

    def watch_window(self, window: QQuickWindow):
        self._window = window
        window.frameSwapped.connect(self._visible)
        window.update()

    @Slot()
    def _visible(self):
        if not self._announced:
            self._announced = True
            # This is a one-time lowering of the already mapped X11 window.
            # Never raise, reactivate or remap it over a running machine UI.
            self._window.lower()
            print(json.dumps({"kioskStatus": "visible", "phase": self._phase}), flush=True)

    def _read_phase(self):
        root = os.open(LOG_ROOT, DIRECTORY_FLAGS)
        try:
            candidates = []
            with os.scandir(root) as entries:
                for index, entry in enumerate(entries):
                    if index >= 4096:
                        break
                    if RUN_NAME.fullmatch(entry.name):
                        info = entry.stat(follow_symlinks=False)
                        if stat.S_ISDIR(info.st_mode):
                            candidates.append((info.st_mtime_ns, entry.name))
            if not candidates:
                return ""
            run = os.open(max(candidates)[1], DIRECTORY_FLAGS, dir_fd=root)
            try:
                descriptor = os.open(
                    "state.json",
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                    dir_fd=run,
                )
                with os.fdopen(descriptor, "rb") as stream:
                    info = os.fstat(stream.fileno())
                    if not stat.S_ISREG(info.st_mode) or info.st_size > 16384:
                        return ""
                    record = json.loads(stream.read(16385))
                phase = record.get("phase", "") if isinstance(record, dict) else ""
                return phase if isinstance(phase, str) else ""
            finally:
                os.close(run)
        finally:
            os.close(root)

    @Slot()
    def _refresh(self):
        try:
            phase = self._read_phase()
        except (OSError, ValueError):
            phase = ""
        if phase not in {"starting", "ready", "recovering", "retained", "stopped"}:
            phase = "starting" if time.monotonic() - self._started < 30 else "unavailable"
        if phase != self._phase:
            self._phase = phase
            self.changed.emit()

    def close(self):
        self._timer.stop()
