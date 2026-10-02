pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import BetterCnc.Ui 1.0
import BetterCnc.Catalog 1.0

Rectangle {
    id: root

    required property ManualState presentation
    property bool compact: false
    signal dialogRequested(string actionId, string title, string axis)

    objectName: "manualPanel"
    implicitWidth: compact ? 264 : 296
    color: Theme.sidebar
    clip: true

    QtObject {
        id: values
        property real feed: 100
        property real rapid: 100
        property real spindle: 100
        property real jog: 600
        property real maxVelocity: 3000
    }

    Connections {
        target: root.Window.window
        function onActiveFocusItemChanged() {
            const focused = root.Window.window.activeFocusItem;
            if (!focused) return;
            let ancestor = focused;
            while (ancestor && ancestor !== contentColumn) ancestor = ancestor.parent;
            if (!ancestor) return;
            const top = focused.mapToItem(contentColumn, 0, 0).y;
            const bottom = top + focused.height;
            const requested = top < scroller.contentY ? top
                : bottom > scroller.contentY + scroller.height ? bottom - scroller.height
                : scroller.contentY;
            scroller.contentY = Math.max(0, Math.min(scroller.contentHeight - scroller.height, requested));
        }
    }

    Flickable {
        id: scroller
        objectName: "manualScroller"
        anchors.fill: parent
        anchors.rightMargin: 1
        contentWidth: width
        contentHeight: contentColumn.height
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick
        clip: true
        ScrollBar.vertical: UiScrollBar {}

        Column {
            id: contentColumn
            width: scroller.width

            Item {
                width: parent.width
                height: 44

                Row {
                    id: tabs
                    x: 12
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4

                    function selectTab(tab) {
                        root.presentation.controlTab = tab;
                        (tab === "manual" ? manualTabButton : mdiTabButton).forceActiveFocus(Qt.TabFocusReason);
                    }

                    UiButton {
                        id: manualTabButton
                        objectName: "manualTab"
                        text: "手动操作 [F3]"
                        kind: "tab"
                        selected: root.presentation.controlTab === "manual"
                        Accessible.role: Accessible.PageTab
                        Accessible.name: text
                        onClicked: root.presentation.controlTab = "manual"
                        Keys.onLeftPressed: tabs.selectTab("mdi")
                        Keys.onRightPressed: tabs.selectTab("mdi")
                        Keys.onPressed: event => {
                            if (event.key === Qt.Key_Home || event.key === Qt.Key_End) {
                                tabs.selectTab(event.key === Qt.Key_Home ? "manual" : "mdi");
                                event.accepted = true;
                            }
                        }
                    }

                    UiButton {
                        id: mdiTabButton
                        objectName: "mdiTab"
                        text: "手动输入 [F5]"
                        kind: "tab"
                        selected: root.presentation.controlTab === "mdi"
                        Accessible.role: Accessible.PageTab
                        Accessible.name: text
                        onClicked: root.presentation.controlTab = "mdi"
                        Keys.onLeftPressed: tabs.selectTab("manual")
                        Keys.onRightPressed: tabs.selectTab("manual")
                        Keys.onPressed: event => {
                            if (event.key === Qt.Key_Home || event.key === Qt.Key_End) {
                                tabs.selectTab(event.key === Qt.Key_Home ? "manual" : "mdi");
                                event.accepted = true;
                            }
                        }
                    }
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.border
                }
            }

            Item {
                id: manualArea
                readonly property int panelPadding: root.compact ? 12 : 18
                readonly property int verticalPadding: root.compact ? 12 : 16
                width: parent.width
                height: visible ? manualContent.height + verticalPadding * 2 : 0
                visible: root.presentation.controlTab === "manual"

                Column {
                    id: manualContent
                    x: manualArea.panelPadding
                    y: manualArea.verticalPadding
                    width: parent.width - manualArea.panelPadding * 2

                    RowLayout {
                        width: parent.width
                        height: 30
                        spacing: 7

                        UiText {
                            text: root.presentation.mode === "joint" ? "关节：" : "坐标轴："
                            font.pixelSize: 11
                            color: Theme.secondary
                            Layout.preferredWidth: 53
                            Layout.fillHeight: true
                            verticalAlignment: Text.AlignVCenter
                        }

                        RowLayout {
                            id: axisSelector
                            spacing: 5
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            function selectAxis(index) {
                                const next = (index + Catalog.axes.length) % Catalog.axes.length;
                                root.presentation.selectedAxis = Catalog.axes[next];
                                axisRepeater.itemAt(next).forceActiveFocus(Qt.TabFocusReason);
                            }

                            Repeater {
                                id: axisRepeater
                                model: Catalog.axes

                                RadioButton {
                                    id: axisButton
                                    required property string modelData
                                    required property int index
                                    objectName: "axis" + modelData
                                    text: root.presentation.mode === "joint" ? index.toString() : modelData
                                    checked: root.presentation.selectedAxis === modelData
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 30
                                    padding: 0
                                    hoverEnabled: true
                                    indicator: null
                                    Accessible.name: text

                                    contentItem: Item {
                                        Row {
                                            anchors.centerIn: parent
                                            spacing: 5

                                            Rectangle {
                                                width: 10
                                                height: 10
                                                anchors.verticalCenter: parent.verticalCenter
                                                radius: 5
                                                color: axisButton.checked ? Theme.accentFill : Theme.input
                                                border.width: 1
                                                border.color: axisButton.checked ? Theme.accent : "#5b5d68"

                                                Rectangle {
                                                    anchors.centerIn: parent
                                                    width: 4
                                                    height: 4
                                                    radius: 2
                                                    color: "white"
                                                    visible: axisButton.checked
                                                }
                                            }

                                            UiText {
                                                text: axisButton.text
                                                font.family: Theme.mono
                                                font.pixelSize: 12
                                                color: axisButton.checked ? "#d0caff" : Theme.text
                                            }
                                        }
                                    }

                                    background: Rectangle {
                                        radius: 5
                                        color: axisButton.checked ? Theme.accentSoft : Theme.input
                                        border.width: axisButton.visualFocus ? 2 : 1
                                        border.color: axisButton.visualFocus ? Theme.accent : axisButton.checked ? "#5c537e" : Theme.borderControl
                                    }

                                    onClicked: root.presentation.selectedAxis = modelData
                                    Keys.onLeftPressed: axisSelector.selectAxis(index - 1)
                                    Keys.onRightPressed: axisSelector.selectAxis(index + 1)
                                    Keys.onUpPressed: axisSelector.selectAxis(index - 1)
                                    Keys.onDownPressed: axisSelector.selectAxis(index + 1)
                                }
                            }
                        }
                    }

                    Item {
                        width: 1
                        height: 12
                    }

                    RowLayout {
                        width: parent.width
                        height: 30
                        spacing: 6

                        UiButton {
                            objectName: "jogMinus"
                            text: "−"
                            font.pixelSize: 18
                            Layout.preferredWidth: 40
                            Layout.preferredHeight: 30
                            Accessible.name: "负向点动"
                            onClicked: root.dialogRequested("machine.jog-minus", root.presentation.selectedAxis + " 轴负向点动", "")
                        }

                        UiButton {
                            objectName: "jogPlus"
                            text: "+"
                            font.pixelSize: 18
                            Layout.preferredWidth: 40
                            Layout.preferredHeight: 30
                            Accessible.name: "正向点动"
                            onClicked: root.dialogRequested("machine.jog-plus", root.presentation.selectedAxis + " 轴正向点动", "")
                        }

                        UiComboBox {
                            objectName: "jogIncrement"
                            model: ["连续点动", "0.1000", "0.0100", "0.0010", "0.0001"]
                            Layout.fillWidth: true
                            Layout.preferredHeight: 30
                            Accessible.name: "点动方式与步距"
                        }
                    }

                    Item {
                        width: 1
                        height: 8
                    }

                    RowLayout {
                        width: parent.width
                        height: 30
                        spacing: 5

                        UiButton {
                            objectName: "homeAll"
                            text: "全部回零"
                            font.pixelSize: 11
                            leftPadding: 3
                            rightPadding: 3
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            Layout.preferredHeight: 30
                            onClicked: root.dialogRequested("machine.home-all", "", "")
                        }

                        UiButton {
                            objectName: "workTouchOff"
                            text: "工件对刀"
                            font.pixelSize: 11
                            leftPadding: 3
                            rightPadding: 3
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            Layout.preferredHeight: 30
                            onClicked: root.dialogRequested("machine.touch-off", "工件对刀", root.presentation.selectedAxis)
                        }

                        UiButton {
                            objectName: "toolTouchOff"
                            text: "刀具对刀"
                            font.pixelSize: 11
                            leftPadding: 3
                            rightPadding: 3
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            Layout.preferredHeight: 30
                            onClicked: root.dialogRequested("tool.touch-off", "刀具对刀", root.presentation.selectedAxis)
                        }
                    }

                    Item {
                        width: 1
                        height: 7
                    }

                    UiCheckBox {
                        objectName: "overrideLimits"
                        width: parent.width
                        height: 27
                        text: "临时解除硬限位"
                        checked: false
                        interactive: false
                        onClicked: root.dialogRequested("machine.override-limits", "临时解除硬限位", "")
                    }

                    Item {
                        width: parent.width
                        height: 120

                        Rectangle {
                            y: 13
                            width: parent.width
                            height: 1
                            color: Theme.border
                        }

                        UiText {
                            y: 34
                            width: 53
                            text: "主轴："
                            color: Theme.secondary
                            font.pixelSize: 11
                        }

                        Column {
                            x: 60
                            y: 27
                            width: parent.width - 60
                            spacing: 5

                            RowLayout {
                                width: parent.width
                                height: 28
                                spacing: 5

                                UiButton {
                                    objectName: "spindleCounterclockwise"
                                    iconName: "left"
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 30
                                    Layout.preferredWidth: 60
                                    Layout.preferredHeight: 28
                                    leftPadding: 6
                                    rightPadding: 6
                                    Accessible.name: "主轴反转"
                                    ToolTip.visible: hovered
                                    ToolTip.text: "主轴反转"
                                    onClicked: root.dialogRequested("spindle.ccw", "主轴反转", "")
                                }

                                UiButton {
                                    objectName: "spindleStop"
                                    text: "停止"
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 60
                                    Layout.preferredWidth: 60
                                    Layout.preferredHeight: 28
                                    leftPadding: 6
                                    rightPadding: 6
                                    onClicked: root.dialogRequested("spindle.stop", "主轴停止", "")
                                }

                                UiButton {
                                    objectName: "spindleClockwise"
                                    iconName: "right"
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 30
                                    Layout.preferredWidth: 60
                                    Layout.preferredHeight: 28
                                    leftPadding: 6
                                    rightPadding: 6
                                    Accessible.name: "主轴正转"
                                    ToolTip.visible: hovered
                                    ToolTip.text: "主轴正转"
                                    onClicked: root.dialogRequested("spindle.cw", "主轴正转", "")
                                }
                            }

                            RowLayout {
                                width: parent.width
                                height: 28
                                spacing: 5

                                UiButton {
                                    objectName: "spindleDecrease"
                                    text: "−"
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 28
                                    leftPadding: 6
                                    rightPadding: 6
                                    Accessible.name: "降低主轴转速"
                                    onClicked: root.dialogRequested("spindle.decrease", "降低主轴转速", "")
                                }

                                UiButton {
                                    objectName: "spindleIncrease"
                                    text: "+"
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 28
                                    leftPadding: 6
                                    rightPadding: 6
                                    Accessible.name: "提高主轴转速"
                                    onClicked: root.dialogRequested("spindle.increase", "提高主轴转速", "")
                                }
                            }

                            UiCheckBox {
                                objectName: "spindleBrake"
                                width: parent.width
                                height: 27
                                text: "主轴制动"
                                checked: false
                                interactive: false
                                onClicked: root.dialogRequested("spindle.brake", "主轴制动", "")
                            }
                        }
                    }

                    Item {
                        width: parent.width
                        height: 62

                        UiText {
                            y: 13
                            width: 53
                            text: "冷却："
                            color: Theme.secondary
                            font.pixelSize: 11
                        }

                        Column {
                            x: 60
                            y: 8
                            width: parent.width - 60

                            UiCheckBox {
                                objectName: "mistCoolant"
                                width: parent.width
                                height: 27
                                text: "喷雾冷却"
                                checked: false
                                interactive: false
                                onClicked: root.dialogRequested("coolant.mist", "喷雾冷却", "")
                            }

                            UiCheckBox {
                                objectName: "floodCoolant"
                                width: parent.width
                                height: 27
                                text: "切削液冷却"
                                checked: false
                                interactive: false
                                onClicked: root.dialogRequested("coolant.flood", "切削液冷却", "")
                            }
                        }
                    }
                }
            }

            Item {
                id: mdiArea
                readonly property int panelPadding: root.compact ? 12 : 18
                readonly property int verticalPadding: root.compact ? 12 : 16
                width: parent.width
                height: visible ? 270 + verticalPadding * 2 : 0
                visible: root.presentation.controlTab === "mdi"

                Item {
                    x: mdiArea.panelPadding
                    y: mdiArea.verticalPadding
                    width: parent.width - mdiArea.panelPadding * 2
                    height: 270

                    UiText {
                        height: 18
                        text: "历史指令："
                        font.pixelSize: 12
                        color: Theme.secondary
                    }

                    Rectangle {
                        y: 26
                        width: parent.width
                        height: 160
                        radius: 6
                        color: Theme.input
                        border.width: 1
                        border.color: Theme.border

                        ListView {
                            id: historyList
                            objectName: "mdiHistory"
                            anchors.fill: parent
                            anchors.margins: 6
                            clip: true
                            model: Catalog.fixture.history
                            boundsBehavior: Flickable.StopAtBounds
                            ScrollBar.vertical: UiScrollBar {}
                            Accessible.name: "手动输入历史"

                            delegate: ItemDelegate {
                                id: historyButton
                                required property string modelData
                                required property int index
                                objectName: "mdiHistory" + index
                                width: historyList.width
                                height: 28
                                padding: 0
                                text: modelData
                                hoverEnabled: true

                                contentItem: UiText {
                                    leftPadding: 6
                                    rightPadding: 6
                                    text: historyButton.text
                                    font.family: Theme.mono
                                    font.pixelSize: 12
                                    color: historyButton.hovered || historyButton.visualFocus ? Theme.text : Theme.secondary
                                    verticalAlignment: Text.AlignVCenter
                                }

                                background: Rectangle {
                                    radius: 4
                                    color: historyButton.hovered || historyButton.visualFocus ? Theme.accentSoft : "transparent"
                                }

                                onClicked: mdiCommand.text = modelData
                            }
                        }
                    }

                    UiText {
                        y: 202
                        height: 18
                        text: "手动输入指令："
                        font.pixelSize: 12
                        color: Theme.secondary
                    }

                    RowLayout {
                        y: 228
                        width: parent.width
                        height: 32
                        spacing: 4

                        UiTextField {
                            id: mdiCommand
                            objectName: "mdiCommand"
                            Layout.fillWidth: true
                            Layout.preferredHeight: 32
                            font.family: Theme.mono
                            Accessible.name: "手动输入指令："
                            selectByMouse: true
                            onAccepted: root.dialogRequested("mdi.go", "执行手动指令", "")
                        }

                        UiButton {
                            objectName: "mdiExecute"
                            text: "执行"
                            Layout.preferredWidth: 48
                            Layout.preferredHeight: 30
                            onClicked: root.dialogRequested("mdi.go", "执行手动指令", "")
                        }
                    }
                }
            }

            Item {
                id: overrides
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
                    x: overrides.panelPadding
                    y: overrides.topPadding + 1
                    height: 18
                    text: "速度与倍率"
                    font.pixelSize: 12
                    font.weight: Font.Medium
                    verticalAlignment: Text.AlignVCenter
                }

                Column {
                    id: ranges
                    x: overrides.panelPadding
                    y: overrides.topPadding + 35
                    width: parent.width - overrides.panelPadding * 2

                    UiRange {
                        objectName: "feedOverride"
                        width: parent.width
                        height: 49
                        label: "进给倍率"
                        to: 120
                        value: values.feed
                        onMoved: value => values.feed = value
                    }

                    UiRange {
                        objectName: "rapidOverride"
                        width: parent.width
                        height: 49
                        label: "快移倍率"
                        to: 100
                        value: values.rapid
                        onMoved: value => values.rapid = value
                    }

                    UiRange {
                        objectName: "spindleOverride"
                        width: parent.width
                        height: 49
                        label: "主轴倍率"
                        to: 120
                        value: values.spindle
                        onMoved: value => values.spindle = value
                    }

                    UiRange {
                        objectName: "jogVelocity"
                        width: parent.width
                        height: 49
                        label: "点动速度"
                        to: 3000
                        value: values.jog
                        unit: "毫米/分钟"
                        onMoved: value => values.jog = value
                    }

                    UiRange {
                        objectName: "maxVelocity"
                        width: parent.width
                        height: 49
                        label: "最大速度"
                        to: 6000
                        value: values.maxVelocity
                        unit: "毫米/分钟"
                        onMoved: value => values.maxVelocity = value
                    }
                }
            }

            Item {
                id: activeCodes
                width: parent.width
                height: visible ? 6 + 17 + 8 + codes.height + 12 : 0
                visible: root.presentation.controlTab === "mdi"

                UiText {
                    x: 18
                    y: 6
                    height: 17
                    text: "当前模态指令："
                    color: Theme.secondary
                    font.pixelSize: 11
                }

                Rectangle {
                    id: codes
                    objectName: "activeCodes"
                    x: 18
                    y: 31
                    width: parent.width - 36
                    height: codeText.implicitHeight + 20
                    color: Theme.input
                    radius: 6
                    border.color: Theme.border
                    border.width: 1

                    UiText {
                        id: codeText
                        x: 10
                        y: 10
                        width: parent.width - 20
                        text: Catalog.fixture.activeCodes
                        color: Theme.secondary
                        font.family: Theme.mono
                        font.pixelSize: 11
                        lineHeightMode: Text.FixedHeight
                        lineHeight: 21
                        wrapMode: Text.Wrap
                    }
                }
            }

            Item {
                width: 1
                height: 10
            }
        }
    }

    Rectangle {
        anchors.right: parent.right
        height: parent.height
        width: 1
        color: Theme.border
    }
}
