pragma ComponentBehavior: Bound
import QtQuick
import BetterCnc.Ui 1.0
import BetterCnc.Catalog 1.0

Column {
    id: root
    required property ToolpathState presentation
    spacing: 8
    readonly property var entries: Catalog.menus.find(menu => menu.id === "view").children
    readonly property var choiceEntries: entries.concat(entries.find(entry => entry.id === "view.grid").children)
    UiText { text: "刀路与坐标显示"; font.pixelSize: 18; font.weight: Font.DemiBold }
    UiText { text: "显示设置即时生效，不改变机床坐标与加工程序。"; color: Theme.secondary }
    Repeater {
        model: [{group: "units", label: "显示单位"}, {group: "view", label: "投影视角"},
                {group: "coordinates", label: "坐标系"}, {group: "position", label: "位置来源"},
                {group: "grid", label: "参考网格"}]
        Row {
            id: choiceRow
            required property var modelData
            readonly property var options: root.choiceEntries.filter(entry => entry.kind === "radio" && entry.group === modelData.group)
            width: root.width; height: 52; spacing: 16
            UiText { width: 136; height: 44; text: choiceRow.modelData.label; verticalAlignment: Text.AlignVCenter }
            UiComboBox {
                objectName: "settings-" + choiceRow.modelData.group
                width: Math.min(400, root.width - 152); height: 44
                optionHeight: 44
                model: choiceRow.options
                textRole: "label"
                currentIndex: choiceRow.options.findIndex(entry => entry.value === root.presentation.choices[choiceRow.modelData.group])
                displayText: currentIndex >= 0 ? currentText : String(root.presentation.choices[choiceRow.modelData.group])
                onActivated: index => root.presentation.setChoice(choiceRow.modelData.group, choiceRow.options[index].value)
            }
        }
    }
    Grid {
        width: parent.width; columns: 2; columnSpacing: 16; rowSpacing: 4
        Repeater {
            model: root.entries.filter(entry => entry.kind === "check" && entry.id in root.presentation.flags)
            UiCheckBox {
                id: flag
                required property var modelData
                objectName: "settings-" + modelData.id
                width: (root.width - 16) / 2; height: 44
                text: modelData.label
                checked: !!root.presentation.flags[modelData.id]
                interactive: false
                onClicked: root.presentation.toggleFlag(modelData.id)
            }
        }
    }
    UiButton {
        objectName: "settings-clear-live"
        text: "清除实际运动轨迹"; height: 44
        onClicked: root.presentation.clearLive()
    }
}
