pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../../qml" as App

QtObject {
    id: harness
    property InteractiveBackend backend: InteractiveBackend { }
    property App.Main mainWindow: App.Main {
        backend: harness.backend
        title: "交互测试 · 无机床连接 — BetterLinuxCNC"
        width: 900
        height: Math.min(820, Screen.desktopAvailableHeight - 60)
        x: 20
        y: 35
        onClosing: Qt.quit()
    }
    property ApplicationWindow controls: ApplicationWindow {
        id: panel
        objectName: "interactiveTestPanel"
        visible: true
        title: "GUI 测试控制台 · 测试数据"
        width: 430
        height: Math.min(820, Screen.desktopAvailableHeight - 60)
        minimumWidth: 380
        minimumHeight: 580
        x: Math.min(harness.mainWindow.x + harness.mainWindow.width + 10, Screen.desktopAvailableWidth - width)
        y: 35
        onClosing: Qt.quit()

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10
            Label { text: "交互式 GUI 测试"; font.pixelSize: 22; font.bold: true }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "左侧操作真实界面，下面查看请求。按钮仅记录操作；用此面板注入反馈，不会连接或控制机床。矩形刀路是固定测试数据。"
            }
            RowLayout {
                Button { text: "显示主界面"; onClicked: { harness.mainWindow.raise(); harness.mainWindow.requestActivate(); } }
                Button { text: "重置测试"; onClicked: harness.backend.reset() }
            }
            Label { text: "1. 注入机床状态"; font.bold: true }
            Flow {
                Layout.fillWidth: true
                spacing: 4
                Repeater {
                    model: [
                        {label: "就绪", state: "ready"}, {label: "断开", state: "offline"},
                        {label: "未上电", state: "power-off"}, {label: "急停", state: "estop"},
                        {label: "运行中", state: "running"}, {label: "暂停", state: "paused"}
                    ]
                    Button {
                        required property var modelData
                        text: modelData.label
                        onClicked: harness.backend.scenario(modelData.state)
                    }
                }
            }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "连接：" + harness.backend.snapshot.connected + "  上电：" + harness.backend.snapshot.powered
                    + "  急停：" + harness.backend.snapshot.estop + "\n模式：" + harness.backend.snapshot.mode
                    + "  忙碌：" + harness.backend.snapshot.busy + "  停止点动调用：" + harness.backend.stopCount
            }
            Label { text: "2. 注入坐标 / 执行行"; font.bold: true }
            Repeater {
                model: ["X", "Y", "Z"]
                RowLayout {
                    id: positionRow
                    required property string modelData
                    required property int index
                    Layout.fillWidth: true
                    Label { text: positionRow.modelData; Layout.preferredWidth: 20 }
                    Slider {
                        Layout.fillWidth: true
                        from: -50; to: 50; stepSize: 1
                        value: harness.backend.snapshot.actualPosition[positionRow.index]
                        onMoved: harness.backend.setPosition(positionRow.index, value)
                    }
                    Label { text: Number(harness.backend.snapshot.actualPosition[positionRow.index]).toFixed(0); Layout.preferredWidth: 35 }
                }
            }
            RowLayout {
                Label { text: "执行行" }
                SpinBox {
                    from: 0; to: harness.backend.document.lines.length
                    value: harness.backend.snapshot.currentLine
                    onValueModified: harness.backend.update({currentLine: value})
                }
                Button { text: "加载示例"; onClicked: harness.backend.loadSample() }
            }
            RowLayout {
                Button { text: "操作报错"; onClicked: harness.backend.errorOccurred("注入测试错误：当前操作被拒绝") }
                Button { text: "预览失败"; onClicked: { harness.backend.document.segments = []; harness.backend.document.previewError = "注入测试错误：第 3 行解释失败"; } }
            }
            RowLayout {
                Label { text: "3. 操作请求（最多 100 条）"; font.bold: true; Layout.fillWidth: true }
                Button { text: "清空"; onClicked: harness.backend.clearRequests() }
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 80
                TextArea {
                    objectName: "interactiveRequestLog"
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.WrapAnywhere
                    placeholderText: "在主界面点击运行、主轴、点动，或输入 MDI；请求将在这里出现。"
                    text: harness.backend.requests.slice().reverse().map(entry =>
                        "#" + entry.sequence + " " + entry.id + "\n" + JSON.stringify(entry.payload)).join("\n\n")
                }
            }
        }
    }
}
