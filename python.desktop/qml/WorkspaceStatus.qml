import QtQuick
import BetterCnc.Ui 1.0
import BetterCnc.Chrome 1.0

Rectangle {
    id: root
    property var machine: ({})
    height: 32
    color: Theme.surface
    MachineStatus { id: status; machine: root.machine }
    Rectangle { width: parent.width; height: 1; color: Theme.border }
    Row {
        x: Theme.padding
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8
        Rectangle { width: 8; height: 8; radius: 4; color: status.tone; anchors.verticalCenter: parent.verticalCenter }
        UiText { objectName: "machineStatusLabel"; text: status.label; color: status.tone; font.pixelSize: Theme.labelSize }
        UiText {
            text: root.machine.connected ? "  /  " + (root.machine.machineName || "LinuxCNC") : "  /  等待本地控制服务"
            color: Theme.secondary
            font.pixelSize: Theme.labelSize
        }
    }
    UiText {
        anchors.right: parent.right
        anchors.rightMargin: Theme.padding
        anchors.verticalCenter: parent.verticalCenter
        text: "刀路预览 · 非材料去除仿真"
        color: Theme.secondary
        font.pixelSize: Theme.labelSize
    }
}
