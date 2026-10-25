import QtQuick
import BetterCnc.Ui 1.0

// Presentation mapping only. Action permissions remain in ChromeActions/service.
QtObject {
    property var machine: ({})
    readonly property string label: !machine.connected ? (machine.connecting ? "正在连接" : "未连接")
        : machine.estop ? "急停已触发"
        : machine.commandState === "error" || machine.commandState === "unknown" ? "操作异常"
        : !machine.powered ? "未上电"
        : machine.paused ? "已暂停" : machine.busy ? "加工中" : "就绪"
    readonly property color tone: !machine.connected ? Theme.secondary
        : machine.estop || machine.commandState === "error" || machine.commandState === "unknown" ? Theme.danger
        : !machine.powered || machine.paused ? Theme.warning : Theme.success
}
