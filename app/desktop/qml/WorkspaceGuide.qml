pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import BetterCnc.Ui 1.0
import BetterCnc.Chrome 1.0

// Guidance describes observed facts, never grants controller permissions.
Rectangle {
    id: root
    objectName: "workspaceGuide"
    required property ChromeActions actions
    property string stage: "prepare"
    readonly property var machine: actions.machine
    readonly property var program: actions.program
    readonly property bool hasProgram: !!program && !!program.filePath
    readonly property string previewState: !hasProgram ? "等待程序" : program.previewBusy ? "解释中…"
        : program.previewError ? "解释失败" : program.segments && program.segments.length ? "刀路已生成" : "暂无刀路线段"
    signal stageRequested(string stage)
    color: Theme.surface
    UiDivider { height: parent.height; width: 1; vertical: true }
    MachineStatus { id: status; machine: root.machine }
    Connections {
        target: root.Window.window
        function onActiveFocusItemChanged() {
            const focused = root.Window.window.activeFocusItem;
            if (!focused) return;
            let ancestor = focused;
            while (ancestor && ancestor !== contents) ancestor = ancestor.parent;
            if (!ancestor) return;
            const top = focused.mapToItem(contents, 0, 0).y + contents.y;
            const targetY = top < scroller.contentY ? top
                : top + focused.height > scroller.contentY + scroller.height ? top + focused.height - scroller.height : scroller.contentY;
            scroller.contentY = Math.max(0, Math.min(scroller.contentHeight - scroller.height, targetY));
        }
    }
    Flickable {
        id: scroller
        objectName: "guideScroller"
        anchors.fill: parent; anchors.margins: 1; anchors.bottomMargin: actionDock.height
        contentWidth: width; contentHeight: contents.height + 32
        boundsBehavior: Flickable.StopAtBounds; clip: true
        ScrollBar.vertical: UiScrollBar { }
        Column {
            id: contents
            x: 16; y: 16; width: parent.width - 32; spacing: 16
            UiText { text: root.stage === "prepare" ? "从一个程序开始" : "检查后再加工"; font.pixelSize: Theme.titleSize; font.weight: Font.DemiBold }
            UiText {
                width: parent.width; wrapMode: Text.Wrap; color: Theme.secondary
                text: root.stage === "prepare" ? "打开 G 代码，确认程序内容，再检查刀路与机床坐标。" : "核对工件原点、刀具和装夹。刀路预览不检查碰撞，也不表示机床已准备完成。"
            }
            Rectangle {
                width: parent.width; height: 76; color: "transparent"
                UiDivider { width: parent.width }
                Column {
                    x: 12; y: 12; spacing: 6; width: parent.width - 24
                    UiText { text: "设备状态"; color: Theme.secondary; font.pixelSize: Theme.labelSize }
                    UiText { text: status.label; color: status.tone; font.pixelSize: 20; font.weight: Font.Medium }
                }
            }
            Repeater {
                model: [
                    {label: "当前程序", value: root.hasProgram ? root.program.fileName : "尚未打开", error: false},
                    {label: "刀路解释", value: root.previewState, error: !!root.program && !!root.program.previewError},
                    {label: "执行行", value: root.machine.connected && root.machine.currentLine > 0 ? String(root.machine.currentLine) : "—", error: false}
                ]
                Column {
                    id: fact
                    required property var modelData
                    width: contents.width; spacing: 4
                    UiText { text: fact.modelData.label; color: Theme.secondary; font.pixelSize: Theme.labelSize }
                    UiText {
                        width: parent.width; text: fact.modelData.value ?? "—"; elide: Text.ElideMiddle
                        color: fact.modelData.error ? Theme.danger : Theme.text
                    }
                }
            }
            UiDivider { width: parent.width; height: 1 }
            UiText {
                width: parent.width; wrapMode: Text.Wrap; color: Theme.secondary; font.pixelSize: Theme.labelSize
                text: "需要 MDI、倍率或完整工具栏？可随时切换专业界面，当前程序与显示设置会保留。"
            }
        }
    }
    Rectangle {
        id: actionDock
        anchors.bottom: parent.bottom; width: parent.width; height: 128
        color: Theme.surface
        UiDivider { x: 16; width: parent.width - 32; height: 1 }
        Column {
            x: 16; y: 16; width: parent.width - 32; spacing: 8
            UiButton {
                objectName: "guide-open"; width: parent.width; height: 44; text: "打开加工程序"; iconName: "folder"
                visible: root.stage === "prepare"; enabled: root.actions.canActivate("file.open")
                onClicked: root.actions.activate("file.open")
            }
            UiButton {
                objectName: "guide-next"; width: parent.width; height: 44; kind: "primary"
                text: root.stage === "prepare" ? "检查刀路 →" : "设备控制与对刀 →"
                onClicked: root.stageRequested(root.stage === "prepare" ? "preview" : "device")
            }
            UiButton {
                objectName: "guide-run"; width: parent.width; height: 44; text: "开始加工"; iconName: "play"
                visible: root.stage === "preview"; enabled: root.actions.canActivate("program.run")
                onClicked: root.actions.activate("program.run")
            }
        }
    }

}
