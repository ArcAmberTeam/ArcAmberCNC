#!/usr/bin/env python3
"""Manual GUI testing with a QML fixture; no service or machine connection."""

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle


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


if __name__ == "__main__":
    raise SystemExit(main())
