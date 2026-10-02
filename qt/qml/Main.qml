import QtQuick
import QtQuick.Controls.Basic
import BetterCnc.Ui 1.0

ApplicationWindow {
    id: window
    objectName: "mainWindow"
    width: 1100
    height: 820
    minimumWidth: 760
    minimumHeight: 640
    visible: true
    title: "axis.ngc — BetterLinuxCNC"
    color: Theme.base
    font.family: Theme.fontFamily
    font.pixelSize: 13
    Workspace {
        anchors.fill: parent
        focusedItem: window.activeFocusItem
    }
}
