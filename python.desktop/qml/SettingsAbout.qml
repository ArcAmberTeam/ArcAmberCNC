pragma ComponentBehavior: Bound
import QtQuick
import BetterCnc.Ui 1.0
import BetterCnc.Chrome 1.0

Column {
    id: root
    property var machine: ({})
    spacing: 0
    MachineStatus { id: status; machine: root.machine }
    readonly property var facts: [
        {label: "应用", value: Qt.application.name || "BetterLinuxCNC"},
        {label: "应用版本", value: Qt.application.version || "—"},
        {label: "操作系统", value: ({osx: "macOS", linux: "Linux", windows: "Windows"})[Qt.platform.os] || Qt.platform.os},
        {label: "机床状态", value: status.label, tone: status.tone},
        {label: "机床名称", value: machine.connected ? machine.machineName || "—" : "—"},
        {label: "配置文件", value: machine.connected ? machine.iniPath || "—" : "—"},
        {label: "配置轴", value: machine.connected && machine.axes?.length ? machine.axes.join(" · ") : "—"}
    ]
    Repeater {
        model: root.facts
        Item {
            id: fact
            required property var modelData
            width: root.width; height: Math.max(56, value.implicitHeight + 28)
            UiText { y: 16; width: 116; text: fact.modelData.label; color: Theme.secondary }
            UiText {
                id: value
                objectName: "settings-about-" + fact.modelData.label
                x: 132; y: 16; width: parent.width - x
                text: fact.modelData.value
                color: fact.modelData.tone || Theme.text
                wrapMode: Text.WrapAnywhere
            }
            UiDivider { anchors.bottom: parent.bottom; width: parent.width }
        }
    }
}
