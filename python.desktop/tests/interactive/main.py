<<<<<<< Updated upstream
#!/usr/bin/env python3
"""Manual GUI testing with a QML fixture; no service or machine connection."""

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt, QTimer, QUrl
=======
"""Run original QML/desktop/service against externally injected LinuxCNC APIs."""
import argparse
import json
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QSettings, Qt, QTimer, QUrl
>>>>>>> Stashed changes
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

<<<<<<< Updated upstream

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar)
    app = QGuiApplication([sys.argv[0]])
    app.setApplicationName("BetterLinuxCNC GUI Test")
    QQuickStyle.setStyle("Basic")
    directory = Path(__file__).resolve().parent
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(directory.parents[1] / "qml"))
    engine.load(QUrl.fromLocalFile(str(directory / "Interactive.qml")))
    if not engine.rootObjects():
        return 1
    if args.smoke_test:
        QTimer.singleShot(1000, app.quit)
    code = app.exec()
    del engine
    return code
=======
DIRECTORY = Path(__file__).resolve().parent.parent
ROOT = DIRECTORY.parent.parent
sys.path[:0] = [str(DIRECTORY), str(ROOT / "python.desktop/python"), str(ROOT / "python.service/src")]

from bettercnc.desktop import DesktopBackend
from interactive.backend import TestConsole
from interactive.linear_program import read_linear_program
from interactive.service_host import ServiceHost


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program", type=Path, default=DIRECTORY / "programs/rectangle-demo.ngc")
    parser.add_argument("--report", type=Path, help="Write a local JSON interface audit")
    parser.add_argument("--capture", type=Path, help="Capture the initial window and exit")
    parser.add_argument("--interface", choices=("guided", "professional"), default="guided")
    args = parser.parse_args()
    try:
        data = read_linear_program(args.program)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar)
    app = QGuiApplication([sys.argv[0]])
    QQuickStyle.setStyle("Basic")
    host = ServiceHost().start()
    # Only a private copy can be edited through the tested application's Save.
    program = host.folder / args.program.name
    program.write_text(data["text"], encoding="utf-8")
    desktop = DesktopBackend(socket_path=str(host.socket), ini_path=str(host.ini),
                             settings=QSettings(str(host.folder / "desktop.ini"), QSettings.Format.IniFormat))
    app.installEventFilter(desktop)
    console = TestConsole(host.vendor, desktop)
    engine = QQmlApplicationEngine()
    target = DIRECTORY.parent / "qml/Main.qml"
    engine.addImportPath(str(target.parent))
    engine.setInitialProperties({"backend": desktop, "width": 1280, "height": 860,
                                 "interfaceMode": args.interface, "guidedStage": "preview"})
    try:
        engine.load(QUrl.fromLocalFile(str(target)))
        if not engine.rootObjects():
            return 1
        tested_window = engine.rootObjects()[0]
        engine.setInitialProperties({"backend": console, "testedWindow": tested_window})
        engine.load(QUrl.fromLocalFile(str(DIRECTORY / "interactive/Controls.qml")))
        if len(engine.rootObjects()) != 2:
            return 1
        tested_window.closing.connect(app.quit)
        loaded = False
        def load_program():
            nonlocal loaded
            if not loaded and desktop.snapshot.get("connected"):
                loaded = True
                desktop.openProgram(str(program))
        desktop.snapshotChanged.connect(load_program)
        load_program()
        def report():
            if args.report:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                temporary = args.report.with_suffix(".tmp")
                result = console.report()
                result["injection"] = {"target": str(target), "desktop": "bettercnc.desktop.DesktopBackend",
                                       "service": "betterlinuxcnc_service.serve", "socket": str(host.socket),
                                       "vendor": "test LinuxCNC Python API", "preview": "restricted G0/G1 fixture"}
                temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                temporary.replace(args.report)
        reporter = QTimer()
        reporter.setInterval(250)
        reporter.timeout.connect(report)
        if args.report:
            reporter.start()
        if args.capture:
            def capture():
                args.capture.parent.mkdir(parents=True, exist_ok=True)
                app.exit(0 if tested_window.grabWindow().save(str(args.capture)) else 1)
            QTimer.singleShot(2000, capture)
        result = app.exec()
        report()
        return result
    finally:
        console.timer.stop()
        desktop.close()
        del engine
        host.close()
>>>>>>> Stashed changes


if __name__ == "__main__":
    raise SystemExit(main())
