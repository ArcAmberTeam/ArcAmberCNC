"""Independent test console; the production window uses real DesktopBackend."""
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot


class TestConsole(QObject):
    changed = Signal()

    def __init__(self, vendor, desktop):
        super().__init__()
        self.vendor, self.desktop = vendor, desktop
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.changed)
        self.timer.start()

    simulationStatus = Property(str, lambda self: self.vendor.diagnostics()["status"], notify=changed)
    progress = Property(float, lambda self: self.vendor.diagnostics()["progress"], notify=changed)
    snapshot = Property("QVariantMap", lambda self: self.desktop.snapshot, notify=changed)
    available = Property(bool, lambda self: self.vendor.diagnostics()["available"], notify=changed)

    @Slot(float)
    def setPlaybackRate(self, value):
        self.vendor.inject("rate", value)

    @Slot()
    def toggleConnection(self):
        self.vendor.inject("connection", not self.available)

    @Slot()
    def emergencyStop(self):
        self.vendor.inject("estop")

    @Slot()
    def driveAlarm(self):
        self.vendor.inject("error")

    def report(self):
        return {"vendor": self.vendor.diagnostics(), "desktop": self.desktop.snapshot}
