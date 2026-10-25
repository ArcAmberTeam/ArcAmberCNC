import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import BetterCnc.Ui 1.0

ApplicationWindow {
    id: window
    objectName: "mainWindow"
    property var backend: null
    property bool kioskMode: false
    property bool startFullscreen: false
    property alias interfaceMode: workspace.interfaceMode
    property alias guidedStage: workspace.guidedStage
    width: 1024
    height: 600
    minimumWidth: 760
    minimumHeight: 600
    visible: true
    visibility: kioskMode || startFullscreen ? Window.FullScreen : Window.Windowed
    flags: kioskMode ? Qt.Window | Qt.FramelessWindowHint : Qt.Window
    onVisibilityChanged: {
        if (kioskMode && window.visibility !== Window.FullScreen)
            Qt.callLater(function() { if (window.kioskMode) window.showFullScreen(); });
    }
    title: backend && backend.program && backend.program.fileName ? backend.program.fileName : "未打开程序"
    color: Theme.base
    font.family: Theme.fontFamily
    font.pixelSize: Theme.bodySize
    onActiveChanged: if (!active) workspace.stopJog()
    onClosing: function(close) {
        workspace.stopJog();
        if (kioskMode)
            close.accepted = false;
        else if (backend && typeof backend.requestClose === "function")
            close.accepted = backend.requestClose();
    }
    onActiveFocusItemChanged: workspace.stopJog()
    Workspace {
        id: workspace
        backend: window.backend
        kioskMode: window.kioskMode
        onQuitRequested: window.close()
        anchors.fill: parent
        focusedItem: window.activeFocusItem
    }
}
