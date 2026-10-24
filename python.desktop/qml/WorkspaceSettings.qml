pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import BetterCnc.Ui 1.0
import BetterCnc.Manual 1.0
import BetterCnc.Toolpath 1.0
import BetterCnc.Chrome 1.0

// Full-window composition; all machine state and commands use the shared APIs.
Rectangle {
    id: root
    objectName: "settingsPage"
    required property ToolpathState preview
    required property ChromeActions actions
    property string interfaceMode: "professional"
    property string section: "interface"
    signal backRequested()
    signal interfaceModeRequested(string mode)
    signal commandRequested(string actionId, var payload)
    function focusBack() { backButton.forceActiveFocus(Qt.TabFocusReason); }
    onSectionChanged: scroller.contentY = 0
    color: Theme.base
    Rectangle {
        id: header
        width: parent.width; height: 64
        color: Theme.surface
        UiButton {
            id: backButton
            objectName: "settings-back"
            x: 16; anchors.verticalCenter: parent.verticalCenter
            width: 124; height: 44; text: "← 返回工作台"
            onClicked: root.backRequested()
        }
        UiText { x: 160; anchors.verticalCenter: parent.verticalCenter; text: "设置"; font.pixelSize: 22; font.weight: Font.DemiBold }
        Row {
            anchors.right: parent.right; anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter; spacing: 12
            UiButton {
                objectName: "settings-estop"
                text: "急停"; iconName: "octagon"; kind: "danger"; width: 100; height: 44
                enabled: root.actions.canActivate("machine.estop")
                onClicked: root.actions.activate("machine.estop")
            }
            UiButton {
                objectName: "settings-stop"
                text: "停止"; iconName: "stop"; kind: "danger"; width: 100; height: 44
                enabled: root.actions.canActivate("program.stop")
                onClicked: root.actions.activate("program.stop")
            }
        }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
    }
    Row {
        id: navigation
        x: 24; y: header.height + 12; spacing: 8
        Repeater {
            model: [{id: "interface", text: "界面布局"}, {id: "display", text: "刀路与坐标"}, {id: "machine", text: "加工选项"}]
            UiButton {
                required property var modelData
                objectName: "settings-tab-" + modelData.id
                text: modelData.text; width: 144; height: 44; kind: "tab"
                selected: root.section === modelData.id
                onClicked: root.section = modelData.id
            }
        }
    }
    Flickable {
        id: scroller
        objectName: "settingsScroller"
        x: 24; y: navigation.y + navigation.height + 16
        width: parent.width - 48; height: parent.height - y - 16
        contentWidth: width; contentHeight: content.height
        clip: true; boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: UiScrollBar { }
        Column {
            id: content
            width: parent.width - 16; spacing: 20
            Column {
                visible: root.section === "interface"
                width: parent.width; spacing: 16
                UiText { text: "选择工作界面"; font.pixelSize: 18; font.weight: Font.DemiBold }
                UiText { width: parent.width; text: "两种布局共享程序和视图状态。选择后返回工作台继续操作。"; color: Theme.secondary; wrapMode: Text.WordWrap }
                Row {
                    width: parent.width; spacing: 16
                    UiButton {
                        objectName: "interface-guided"
                        width: (parent.width - 16) / 2; height: 88; kind: "tab"
                        text: "简易 · 准备 → 检查 → 加工"
                        selected: root.interfaceMode === "guided"
                        onClicked: root.interfaceModeRequested("guided")
                    }
                    UiButton {
                        objectName: "interface-professional"
                        width: (parent.width - 16) / 2; height: 88; kind: "tab"
                        text: "专业 · 手动 / 刀路 / 程序同屏"
                        selected: root.interfaceMode === "professional"
                        onClicked: root.interfaceModeRequested("professional")
                    }
                }
                UiText {
                    width: parent.width; wrapMode: Text.WordWrap
                    text: "显示偏好在本次运行中保留；退出程序后恢复默认。"
                    color: Theme.secondary
                }
            }
            ToolpathSettings {
                width: parent.width
                visible: root.section === "display"
                presentation: root.preview
            }
            Column {
                width: parent.width; spacing: 16
                visible: root.section === "machine"
                UiText { text: "程序执行选项"; font.pixelSize: 18; font.weight: Font.DemiBold }
                UiText { width: parent.width; wrapMode: Text.WordWrap; text: "开关状态以控制器反馈为准。设置页内不会响应点动或运行快捷键。"; color: Theme.secondary }
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
                ManualSettings {
                    width: parent.width
                    machine: root.actions.machine
                    onCommandRequested: (actionId, payload) => root.commandRequested(actionId, payload)
                }
            }
        }
    }
    Connections {
        target: root.Window.window
        function onActiveFocusItemChanged() {
            if (!root.visible) return;
            const item = root.Window.window.activeFocusItem;
            let ancestor = item;
            while (ancestor && ancestor !== content) ancestor = ancestor.parent;
            if (!ancestor || !item) return;
            const top = item.mapToItem(content, 0, 0).y;
            const bottom = top + item.height;
            scroller.contentY = Math.max(0, Math.min(scroller.contentHeight - scroller.height,
                top < scroller.contentY ? top : bottom > scroller.contentY + scroller.height ? bottom - scroller.height : scroller.contentY));
        }
    }
}
