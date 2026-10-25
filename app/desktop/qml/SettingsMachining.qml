pragma ComponentBehavior: Bound
import QtQuick
import BetterCnc.Ui 1.0
import BetterCnc.Manual 1.0
import BetterCnc.Chrome 1.0

Column {
    id: root
    required property ChromeActions actions
    signal commandRequested(string actionId, var payload)
    spacing: 20
    Column {
        width: parent.width; spacing: 8
        UiText { text: "程序执行"; font.pixelSize: 18; font.weight: Font.DemiBold }
        Repeater {
            model: [{id: "program.optional", text: "可选停止（M1）"}, {id: "program.block-delete", text: "跳过 / 标记程序行"}]
            UiCheckBox {
                required property var modelData
                objectName: "settings-" + modelData.id
                text: modelData.text; height: 44; width: parent.width
                checked: root.actions.isSelected({id: modelData.id})
                interactive: false
                enabled: root.actions.canActivate(modelData.id)
                onClicked: root.actions.activate(modelData.id)
            }
        }
    }
    UiDivider { width: parent.width }
    ManualSettings {
        width: parent.width
        machine: root.actions.machine
        onCommandRequested: (actionId, payload) => root.commandRequested(actionId, payload)
    }
}
