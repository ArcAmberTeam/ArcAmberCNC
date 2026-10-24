import QtQuick
import QtQuick.Controls.Basic
import BetterCnc.Ui 1.0

ApplicationWindow {
    id: window
    objectName: "mainWindow"
    property var backend: null
    property alias interfaceMode: workspace.interfaceMode
    property alias guidedStage: workspace.guidedStage
    width: 1440
    height: 900
    minimumWidth: 760
    minimumHeight: 640
    visible: true
    title: (backend && backend.program && backend.program.fileName ? backend.program.fileName + " — " : "") + "BetterLinuxCNC"
    color: Theme.base
    font.family: Theme.fontFamily
    font.pixelSize: Theme.bodySize
    onActiveChanged: if (!active) workspace.stopJog()
    onClosing: function(close) {
        workspace.stopJog();
        if (backend && typeof backend.requestClose === "function")
            close.accepted = backend.requestClose();
    }
    onActiveFocusItemChanged: workspace.stopJog()
    Workspace {
        id: workspace
        backend: window.backend
        onQuitRequested: window.close()
        anchors.fill: parent
        focusedItem: window.activeFocusItem
    }
}
