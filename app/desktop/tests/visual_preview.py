"""Launch a visual QA fixture, optionally capture an offscreen test window."""
import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--scenario", choices=("ready", "offline", "error"), default="ready")
    parser.add_argument("--interface", choices=("professional", "guided"), default="professional")
    parser.add_argument("--stage", choices=("prepare", "preview", "device"), default="prepare")
    parser.add_argument("--capture", type=Path)
    args = parser.parse_args()
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar)
    app = QGuiApplication([sys.argv[0]])
    QQuickStyle.setStyle("Basic")
    directory = Path(__file__).resolve().parent
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(directory.parent / "qml"))
    engine.setInitialProperties({"width": args.width, "height": args.height, "scenario": args.scenario, "interfaceMode": args.interface, "guidedStage": args.stage})
    engine.load(QUrl.fromLocalFile(str(directory / "VisualPreview.qml")))
    if not engine.rootObjects():
        return 1
    if args.capture:
        def capture():
            app.exit(0 if engine.rootObjects()[0].grabWindow().save(str(args.capture)) else 1)
        QTimer.singleShot(700, capture)
    result = app.exec()
    del engine
    return result


if __name__ == "__main__":
    raise SystemExit(main())
