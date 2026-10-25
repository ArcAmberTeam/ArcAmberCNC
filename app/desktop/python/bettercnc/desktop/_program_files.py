"""Read-only program browsing confined to the operator's installed data roots."""

from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot


class ProgramFiles(QObject):
    changed = Signal()

    def __init__(self, parent=None, *, roots=None):
        super().__init__(parent)
        self._roots = tuple(
            Path(root).absolute()
            for root in (
                roots or ("/var/lib/betterlinuxcnc/programs", "/var/lib/betterlinuxcnc/inbox")
            )
        )
        self._directory = self._roots[0]
        self._entries = []
        self._message = ""

    locations = Property(
        "QStringList", lambda self: [str(root) for root in self._roots], constant=True
    )
    directory = Property(str, lambda self: str(self._directory), notify=changed)
    entries = Property("QVariantList", lambda self: self._entries, notify=changed)
    message = Property(str, lambda self: self._message, notify=changed)

    def resolve(self, value):
        try:
            path = Path(value).resolve()
        except (OSError, RuntimeError) as error:
            raise ValueError("程序路径无法解析") from error
        if not any(path.is_relative_to(root) for root in self._roots):
            raise ValueError("加工程序只能位于系统程序目录或 CAM 收件目录")
        return path

    @Slot(str, result=bool)
    def browse(self, value):
        try:
            directory = self.resolve(value)
            if not directory.is_dir():
                raise ValueError("程序目录尚未准备好，请联系维护人员")
            entries = []
            for item in directory.iterdir():
                if item.name.startswith("."):
                    continue
                try:
                    path = self.resolve(item)
                except (OSError, ValueError):
                    continue
                if path.is_dir() or path.is_file():
                    entries.append(
                        {"name": item.name, "path": str(path), "directory": path.is_dir()}
                    )
            self._directory = directory
            self._entries = sorted(entries, key=lambda item: (not item["directory"], item["name"]))
            self._message = ""
            self.changed.emit()
            return True
        except (OSError, ValueError) as error:
            self._message = str(error)
            self.changed.emit()
            return False

    @Slot()
    def refresh(self):
        self.browse(str(self._directory))

    @Slot()
    def up(self):
        if self._directory not in self._roots:
            self.browse(str(self._directory.parent))

    @Slot(str, result=str)
    def destination(self, name):
        try:
            if not name or name in (".", "..") or Path(name).name != name or name.startswith("."):
                raise ValueError("请输入不含目录的程序文件名")
            return str(self.resolve(self._directory / name))
        except (OSError, ValueError) as error:
            self._message = str(error)
            self.changed.emit()
            return ""
