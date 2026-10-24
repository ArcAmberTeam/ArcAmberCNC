import QtQuick
import QtQuick.Controls.Basic
import BetterCnc.Ui 1.0

ApplicationWindow {
    id: window
    objectName: "mainWindow"
    property var backend: null
    property alias interfaceMode: workspace.interfaceMode
    property alias guidedStage: workspace.guidedStage
    width: 1024
    height: 600
    minimumWidth: 760
    minimumHeight: 600
    visible: true
    title: backend && backend.program && backend.program.fileName ? backend.program.fileName : "未打开程序"
    color: Theme.base
    font.family: Theme.fontFamily
    font.pixelSize: Theme.bodySize
    onActiveChanged: if (!active) workspace.stopJog()
    onClosing: workspace.stopJog()
    onActiveFocusItemChanged: workspace.stopJog()
    Workspace {
        id: workspace
        backend: window.backend
        onQuitRequested: window.close()
        anchors.fill: parent
        focusedItem: window.activeFocusItem
    }
}
