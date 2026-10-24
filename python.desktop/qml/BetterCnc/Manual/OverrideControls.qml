import QtQuick
import BetterCnc.Ui 1.0

Item {
    id: root
    required property ManualState presentation
    property var machine: ({})
    property bool compact: false
    readonly property bool connected: !!machine.connected
    signal commandRequested(string actionId, var payload)
    signal jogStopRequested()
    function permitted(id) { return connected && (!machine.capabilities || machine.capabilities[id] !== false); }
    readonly property int panelPadding: root.compact ? 12 : 18
    readonly property int topPadding: root.compact ? 14 : 16
    width: parent.width
    height: topPadding + 1 + 34 + ranges.height

    Rectangle {
        width: parent.width
        height: 1
        color: Theme.border
    }

    UiText {
        x: root.panelPadding
        y: root.topPadding + 1
        height: 18
        text: "速度与倍率"
        font.pixelSize: 12
        font.weight: Font.Medium
        verticalAlignment: Text.AlignVCenter
    }

    Column {
        id: ranges
        x: root.panelPadding
        y: root.topPadding + 35
        width: parent.width - root.panelPadding * 2

        UiRange {
            objectName: "feedOverride"
            width: parent.width
            height: 49
            label: "进给倍率"
            to: 120
            value: Number(root.machine.feedOverride || 0) * 100
            valueKnown: root.connected && typeof root.machine.feedOverride === "number" && isFinite(root.machine.feedOverride)
            enabled: valueKnown && root.permitted("override.feed")
            onMoved: value => root.commandRequested("override.feed", {value: value / 100})
        }

        UiRange {
            objectName: "rapidOverride"
            width: parent.width
            height: 49
            label: "快移倍率"
            to: 100
            value: Number(root.machine.rapidOverride || 0) * 100
            valueKnown: root.connected && typeof root.machine.rapidOverride === "number" && isFinite(root.machine.rapidOverride)
            enabled: valueKnown && root.permitted("override.rapid")
            onMoved: value => root.commandRequested("override.rapid", {value: value / 100})
        }

        UiRange {
            objectName: "spindleOverride"
            width: parent.width
            height: 49
            label: "主轴倍率"
            to: 120
            value: Number(root.machine.spindleOverride || 0) * 100
            valueKnown: root.connected && typeof root.machine.spindleOverride === "number" && isFinite(root.machine.spindleOverride)
            enabled: valueKnown && root.permitted("override.spindle")
            onMoved: value => root.commandRequested("override.spindle", {value: value / 100})
        }

        UiRange {
            objectName: "jogVelocity"
            width: parent.width
            height: 49
            label: "点动速度"
            to: Number(root.machine.jogMaxVelocity || root.machine.maxVelocity || 0) * 60
            value: root.presentation.jogVelocity
            enabled: root.connected
            unit: root.machine.linearUnits === 1 ? "毫米/分钟" : "机床单位/分钟"
            onMoved: value => { root.jogStopRequested(); root.presentation.jogVelocity = value; }
        }

        UiRange {
            objectName: "maxVelocity"
            width: parent.width
            height: 49
            label: "最大速度"
            to: Number(root.machine.maxVelocityLimit || root.machine.maxVelocity || 0) * 60
            value: Number(root.machine.maxVelocity || 0) * 60
            valueKnown: root.connected && typeof root.machine.maxVelocity === "number" && isFinite(root.machine.maxVelocity)
            enabled: valueKnown && root.permitted("velocity.max")
            unit: root.machine.linearUnits === 1 ? "毫米/分钟" : "机床单位/分钟"
            onMoved: value => root.commandRequested("velocity.max", {value: value / 60})
        }
    }
}
