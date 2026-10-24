import QtQuick
import BetterCnc.Ui 1.0

// Settings observe the same snapshot and submit through the existing command path.
Column {
    id: root
    property var machine: ({})
    readonly property bool connected: !!machine.connected
    signal commandRequested(string actionId, var payload)
    function permitted(id) { return connected && (!machine.capabilities || machine.capabilities[id] !== false); }
    spacing: 10
    UiText { text: "运动速度上限"; font.pixelSize: 18; font.weight: Font.DemiBold }
    UiText {
        width: parent.width
        text: "修改后等待控制器反馈。点动速度和常用倍率仍在主界面调整。"
        wrapMode: Text.WordWrap; color: Theme.secondary
    }
    UiRange {
        objectName: "maxVelocity"
        width: parent.width
        height: 64
        label: "最大速度"
        to: Number(root.machine.maxVelocityLimit || root.machine.maxVelocity || 0) * 60
        value: Number(root.machine.maxVelocity || 0) * 60
        valueKnown: root.connected && typeof root.machine.maxVelocity === "number" && isFinite(root.machine.maxVelocity)
        enabled: valueKnown && root.permitted("velocity.max")
        unit: root.machine.linearUnits === 1 ? "毫米/分钟" : "机床单位/分钟"
        onMoved: value => root.commandRequested("velocity.max", {value: value / 60})
    }
}
