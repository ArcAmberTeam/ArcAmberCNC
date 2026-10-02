pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import BetterCnc.Ui 1.0
import BetterCnc.Catalog 1.0

Popup {
    id: root
    objectName: "axis-dialog"
    property string actionId: ""
    property string title: ""
    property string axis: "X"
    property string value: "0.0"
    property string coordinateSystem: "G54"
    readonly property string description: {
        if (actionId === "help.about") return "基于 AXIS 的 LinuxCNC 中文操作界面";
        if (actionId === "help.reference") return "快捷键说明：当前仅支持 F3、F5 和视图操作快捷键，机床控制快捷键尚未接入。";
        if (actionId === "file.properties") return "当前内置演示程序的信息。";
        return "尚未连接控制器。当前仅演示界面，此操作不会执行。";
    }
    parent: Overlay.overlay
    popupType: Popup.Item
    width: Math.min(actionId === "help.reference" ? 516
                    : ["file.open", "file.open-sample", "file.save"].indexOf(actionId) >= 0 ? 406
                    : 370, parent ? parent.width * 0.92 : 516)
    height: Math.min(58 + body.implicitHeight + 44, parent ? parent.height * 0.85 : 680)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? parent.height * 0.46 - height / 2 : 0
    padding: 1
    modal: true
    dim: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    enter: Transition { }
    exit: Transition { }
    Overlay.modal: Rectangle { color: "#99000000" }
    background: Rectangle { color: Theme.raised; border.color: "#3b3d45"; radius: 12 }

    function openDialog(id, label, selectedAxis) {
        const item = Catalog.findItem(id);
        actionId = id;
        title = item ? item.label.replace("…", "") : (label || "操作说明");
        axis = selectedAxis || "X";
        value = "0.0";
        open();
    }
    onOpened: closeButton.forceActiveFocus()

    contentItem: Item {
        Item {
            id: titlebar
            width: parent.width
            height: 56
            UiText {
                x: 22
                anchors.verticalCenter: parent.verticalCenter
                text: root.title
                font.weight: Font.DemiBold
                Accessible.role: Accessible.Heading
            }
            UiButton {
                anchors.right: parent.right
                anchors.rightMargin: 18
                anchors.verticalCenter: parent.verticalCenter
                objectName: "dialog-dismiss"
                text: "×"
                kind: "toolbar"
                width: 28
                height: 28
                font.pixelSize: 22
                Accessible.name: "关闭对话框"
                onClicked: root.close()
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
        }
        Flickable {
            id: bodyScroll
            anchors.top: titlebar.bottom
            anchors.bottom: parent.bottom
            width: parent.width
            contentWidth: width
            contentHeight: body.implicitHeight + 44
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: UiScrollBar { }
            Column {
                id: body
                x: 22
                y: 22
                width: bodyScroll.width - 44
                spacing: 0
                UiText {
                    objectName: "dialog-description"
                    width: parent.width
                    text: root.description
                    color: Theme.secondary
                    lineHeightMode: Text.FixedHeight
                    lineHeight: 23.4
                    height: lineCount * 23.4
                    wrapMode: Text.WordWrap
                }
                Item { width: 1; height: 18 }
                Loader {
                    id: detail
                    width: parent.width
                    sourceComponent: {
                        if (root.actionId === "help.about") return aboutContent;
                        if (root.actionId === "help.reference") return referenceContent;
                        if (root.actionId === "file.properties") return propertiesContent;
                        if (["file.open", "file.open-sample", "file.save"].indexOf(root.actionId) >= 0) return fileContent;
                        if (["machine.touch-off", "tool.touch-off"].indexOf(root.actionId) >= 0) return touchContent;
                        if (root.actionId === "view.grid-custom") return gridContent;
                        if (root.actionId === "tool.edit") return toolContent;
                        if (root.actionId === "show.pyvcp") return panelContent;
                        return null;
                    }
                }
                Item { width: 1; height: 24 }
                UiButton {
                    id: closeButton
                    objectName: "dialog-close"
                    anchors.right: parent.right
                    width: 75
                    text: "关闭"
                    onClicked: root.close()
                }
            }
        }
    }

    Component {
        id: aboutContent
        RowLayout {
            spacing: 17
            Image { source: Catalog.axisLogo; Layout.preferredWidth: 48; Layout.preferredHeight: 48; Layout.alignment: Qt.AlignTop }
            Column {
                Layout.fillWidth: true
                spacing: 7
                UiText { text: "AXIS " + Catalog.fixture.version; font.pixelSize: 18; font.bold: true }
                UiText { text: "示例配置：" + Catalog.fixture.machine; font.pixelSize: 13 }
                UiText { text: "中文界面原型 · 仅作展示" }
                UiText { text: "功能与布局参考 AXIS 2.9.10。" }
            }
        }
    }
    Component {
        id: referenceContent
        GridLayout {
            columns: 2
            columnSpacing: 22
            rowSpacing: 7
            Repeater {
                model: Catalog.quickReference.length * 2
                delegate: UiText {
                    required property int index
                    text: Catalog.quickReference[Math.floor(index / 2)][index % 2]
                    font.family: index % 2 === 0 ? Theme.mono : Theme.fontFamily
                    Layout.fillWidth: index % 2 === 1
                }
            }
        }
    }
    Component {
        id: propertiesContent
        GridLayout {
            columns: 2
            columnSpacing: 22
            rowSpacing: 7
            UiText { text: "文件名"; font.bold: true }
            UiText { text: Catalog.fixture.fileName; Layout.fillWidth: true }
            UiText { text: "程序行数"; font.bold: true }
            UiText { text: Catalog.sampleProgram.length }
            UiText { text: "程序来源"; font.bold: true }
            UiText { text: "内置 AXIS 标识演示程序" }
            UiText { text: "刀路预览"; font.bold: true }
            UiText { text: "静态示意图，尚未接入程序解释器"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }
    }
    Component {
        id: fileContent
        ColumnLayout {
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                UiText { text: "文件夹：" }
                UiTextField { Layout.fillWidth: true; text: "/linuxcnc/nc_files"; readOnly: true; Accessible.name: "文件夹" }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 160
                color: Theme.input
                radius: 6
                border.color: Theme.borderControl
                Column {
                    x: 4
                    y: 4
                    width: parent.width - 8
                    Item {
                        width: parent.width
                        height: 24
                        UiText { x: 3; anchors.verticalCenter: parent.verticalCenter; text: "📁  上级目录" }
                    }
                    Rectangle {
                        width: parent.width
                        height: 24
                        color: Theme.accentSoft
                        UiText { x: 3; anchors.verticalCenter: parent.verticalCenter; text: "▤  axis.ngc" }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                UiText { text: "文件名：" }
                UiTextField { Layout.fillWidth: true; text: Catalog.fixture.fileName; readOnly: true; Accessible.name: "文件名" }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                UiText { text: "文件类型：" }
                UiComboBox { Layout.fillWidth: true; model: ["加工程序（*.ngc）", "所有文件（*）"]; Accessible.name: "文件类型" }
            }
        }
    }
    Component {
        id: touchContent
        ColumnLayout {
            spacing: 11
            UiText { text: "设置 " + root.axis + " 轴" + (root.actionId.indexOf("tool") === 0 ? "刀具偏置" : "工件坐标") + "：" }
            RowLayout {
                spacing: 10
                UiText { text: "设定值" }
                UiTextField {
                    objectName: "touch-value"
                    Layout.preferredWidth: 130
                    text: root.value
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    Accessible.name: "设定值"
                    onTextEdited: root.value = text
                }
            }
            RowLayout {
                spacing: 10
                UiText { text: "工件坐标系" }
                UiComboBox {
                    objectName: "touch-coordinate-system"
                    model: Catalog.coordinateSystems
                    currentIndex: Catalog.coordinateSystems.indexOf(root.coordinateSystem)
                    Accessible.name: "工件坐标系"
                    onActivated: root.coordinateSystem = currentText
                }
            }
        }
    }
    Component {
        id: gridContent
        RowLayout {
            spacing: 10
            UiText { text: "网格间距" }
            UiTextField {
                objectName: "grid-spacing"
                Layout.preferredWidth: 130
                text: root.value
                Accessible.name: "网格间距"
                inputMethodHints: Qt.ImhFormattedNumbersOnly
                onTextEdited: root.value = text
            }
            UiText { text: "毫米"; Layout.fillWidth: true }
        }
    }
    Component {
        id: toolContent
        Column {
            height: 65
            Row {
                width: parent.width
                Repeater {
                    model: ["刀具号", "刀位号", "X", "Y", "Z", "直径", "备注"]
                    delegate: Rectangle {
                        id: toolHeading
                        required property string modelData
                        required property int index
                        width: parent.width * (index < 2 ? 0.2 : index > 4 ? 0.15 : 0.1)
                        height: 32
                        color: "transparent"
                        border.color: Theme.borderControl
                        UiText { x: 7; anchors.verticalCenter: parent.verticalCenter; text: toolHeading.modelData; font.bold: true }
                    }
                }
            }
            Rectangle {
                width: parent.width
                height: 33
                color: Theme.input
                border.color: Theme.borderControl
                UiText { x: 7; anchors.verticalCenter: parent.verticalCenter; text: "尚未加载刀具表" }
            }
        }
    }
    Component {
        id: panelContent
        UiText {
            text: "自定义面板需根据具体机床配置。当前三轴演示界面未配置 PyVCP 面板。"
            wrapMode: Text.WordWrap
            lineHeight: 1.5
        }
    }
}
