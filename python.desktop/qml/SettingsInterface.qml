import QtQuick
import BetterCnc.Ui 1.0
import BetterCnc.Toolpath 1.0

Column {
    id: root
    required property ToolpathState preview
    property string interfaceMode: "professional"
    signal interfaceModeRequested(string mode)
    spacing: 24
    Column {
        width: parent.width; spacing: 16
        UiText { text: "工作台布局"; font.pixelSize: 18; font.weight: Font.DemiBold }
        Row {
            width: parent.width; spacing: 12
            UiButton {
                objectName: "interface-guided"
                width: (parent.width - 12) / 2; height: 52; kind: "tab"
                text: "简易界面"
                selected: root.interfaceMode === "guided"
                onClicked: root.interfaceModeRequested("guided")
            }
            UiButton {
                objectName: "interface-professional"
                width: (parent.width - 12) / 2; height: 52; kind: "tab"
                text: "专业界面"
                selected: root.interfaceMode === "professional"
                onClicked: root.interfaceModeRequested("professional")
            }
        }
    }
    UiDivider { width: parent.width }
    ToolpathSettings {
        width: parent.width
        presentation: root.preview
        category: "display"
    }
}
