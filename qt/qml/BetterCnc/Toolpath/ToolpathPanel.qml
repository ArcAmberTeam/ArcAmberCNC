pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Window
import BetterCnc.Ui 1.0
import BetterCnc.Catalog 1.0

Rectangle {
    id: root
    required property ToolpathState presentation
    property bool compact: false
    readonly property bool narrow: Window.window ? Window.window.width <= 900 : width <= 550
    readonly property string zero: presentation.choices.units === "inch" ? "0.0000" : "0.000"
    readonly property string unit: presentation.choices.units === "mm" ? "毫米" : "英寸"
    objectName: "toolpathPanel"
    color: Theme.base
    clip: true

    Rectangle {
        id: tabs
        width: parent.width
        height: 44
        color: Theme.base
        Accessible.role: Accessible.PageTabList
        Accessible.name: "刀路与坐标显示"
        Row {
            x: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4
            UiButton {
                id: previewTab
                objectName: "previewTab"
                kind: "tab"
                text: "刀路预览"
                height: 32
                selected: root.presentation.previewTab === "preview"
                Accessible.role: Accessible.PageTab
                Accessible.name: text
                onClicked: root.presentation.previewTab = "preview"
                Keys.onRightPressed: {
                    droTab.forceActiveFocus();
                    root.presentation.previewTab = "dro";
                }
            }
            UiButton {
                id: droTab
                objectName: "droTab"
                kind: "tab"
                text: "坐标数显"
                height: 32
                selected: root.presentation.previewTab === "dro"
                Accessible.role: Accessible.PageTab
                Accessible.name: text
                onClicked: root.presentation.previewTab = "dro"
                Keys.onLeftPressed: {
                    previewTab.forceActiveFocus();
                    root.presentation.previewTab = "preview";
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
        id: preview
        anchors.top: tabs.bottom
        anchors.bottom: parent.bottom
        width: parent.width
        visible: root.presentation.previewTab === "preview"

        Rectangle {
            id: readout
            width: parent.width
            height: 2 * verticalPadding + contentHeight + 1
            color: Theme.base
            readonly property int horizontalPadding: root.compact ? 16 : 20
            readonly property int verticalPadding: root.compact ? 12 : 15
            readonly property int gapX: root.narrow ? 14 : (root.compact ? 18 : 24)
            readonly property int gapY: root.compact ? 8 : 12
            readonly property real contentWidth: width - 2 * horizontalPadding
            readonly property int valueSize: root.presentation.flags["show.large"] ? 30 : (root.compact ? 20 : 22)
            readonly property real cellWidth: axisMetrics.advanceWidth + valueMetrics.advanceWidth + unitMetrics.advanceWidth + 16
                                              + (root.presentation.flags["show.dtg"] ? dtgMetrics.advanceWidth + 8 : 0)
            readonly property int columns: Math.max(1, Math.min(Catalog.axes.length, Math.floor((contentWidth + gapX) / (cellWidth + gapX))))
            readonly property real rowHeight: valueSize * 1.5
            readonly property int rows: Math.ceil(Catalog.axes.length / columns)
            readonly property real axisHeight: rows * rowHeight + (rows - 1) * gapY
            readonly property bool velocityOnOwnRow: root.compact || columns < Catalog.axes.length
                                                        || Catalog.axes.length * (cellWidth + gapX) + velocity.width > contentWidth
            readonly property real velocityHeight: root.presentation.flags["show.velocity"] && velocityOnOwnRow ? gapY + velocity.height : 0
            readonly property real contentHeight: axisHeight + velocityHeight
                                                    + (root.presentation.flags["show.offsets"] ? gapY + offsets.height : 0)
            Accessible.role: Accessible.Grouping
            Accessible.name: "坐标读数"

            TextMetrics {
                id: axisMetrics
                text: "X"
                font.family: Theme.mono
                font.pixelSize: 12
            }
            TextMetrics {
                id: valueMetrics
                text: root.zero
                font.family: Theme.mono
                font.pixelSize: readout.valueSize
                font.weight: Font.Medium
                font.letterSpacing: -0.7
            }
            TextMetrics {
                id: unitMetrics
                text: root.unit
                font.family: Theme.fontFamily
                font.pixelSize: 10
            }
            TextMetrics {
                id: dtgMetrics
                text: "剩余 " + root.zero
                font.family: Theme.mono
                font.pixelSize: 11
            }
            Repeater {
                model: Catalog.axes
                delegate: Item {
                    id: axisReadout
                    required property string modelData
                    required property int index
                    x: readout.horizontalPadding + (index % readout.columns) * (readout.cellWidth + readout.gapX)
                    y: readout.verticalPadding + Math.floor(index / readout.columns) * (readout.rowHeight + readout.gapY)
                    width: readout.cellWidth
                    height: readout.rowHeight
                    Accessible.role: Accessible.StaticText
                    Accessible.name: modelData + " " + root.zero + " " + root.unit
                    Row {
                        spacing: 8
                        anchors.verticalCenter: parent.verticalCenter
                        UiText {
                            text: axisReadout.modelData
                            font.family: Theme.mono
                            font.pixelSize: 12
                            color: Theme.secondary
                            anchors.baseline: coordinateValue.baseline
                        }
                        UiText {
                            id: coordinateValue
                            objectName: "coordinate" + axisReadout.modelData
                            text: root.zero
                            font.family: Theme.mono
                            font.pixelSize: readout.valueSize
                            font.weight: Font.Medium
                            font.letterSpacing: -0.7
                        }
                        UiText {
                            text: root.unit
                            font.pixelSize: 10
                            color: Theme.muted
                            anchors.baseline: coordinateValue.baseline
                        }
                        UiText {
                            objectName: "distanceToGo" + axisReadout.modelData
                            visible: root.presentation.flags["show.dtg"]
                            text: "剩余 " + root.zero
                            font.family: Theme.mono
                            font.pixelSize: 11
                            color: Theme.secondary
                            anchors.baseline: coordinateValue.baseline
                        }
                    }
                }
            }
            UiText {
                id: velocity
                objectName: "velocityReadout"
                visible: root.presentation.flags["show.velocity"]
                x: readout.velocityOnOwnRow ? readout.horizontalPadding : readout.width - readout.horizontalPadding - width
                y: readout.verticalPadding + (readout.velocityOnOwnRow ? readout.axisHeight + readout.gapY : (readout.rowHeight - height) / 2)
                text: "速度：  " + root.zero
                height: 16.5
                verticalAlignment: Text.AlignVCenter
                font.family: Theme.mono
                font.pixelSize: 11
                color: Theme.secondary
            }
            UiText {
                id: offsets
                objectName: "offsetReadout"
                visible: root.presentation.flags["show.offsets"]
                x: readout.horizontalPadding
                y: readout.verticalPadding + readout.axisHeight + readout.velocityHeight + readout.gapY
                text: "G54 X: 0.000 Y: 0.000 Z: 0.000"
                height: 16.5
                verticalAlignment: Text.AlignVCenter
                font.family: Theme.mono
                font.pixelSize: 11
                color: Theme.secondary
            }
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.border
            }
        }

        ToolpathCanvas {
            id: canvas
            anchors.top: readout.bottom
            anchors.bottom: legend.top
            width: parent.width
            presentation: root.presentation
        }
        UiText {
            objectName: "previewCaption"
            anchors.top: canvas.top
            anchors.topMargin: 14
            anchors.right: parent.right
            anchors.rightMargin: 20
            text: ({"p": "透视图", "z": "俯视图", "z2": "旋转俯视图", "x": "侧视图", "y": "正视图"})[root.presentation.choices.view]
                  + " · " + Math.round(root.presentation.zoom * 100) + "%"
            font.pixelSize: 10
            color: Theme.muted
        }
        Rectangle {
            id: legend
            anchors.bottom: parent.bottom
            width: parent.width
            height: 32
            color: "#17181b"
            Row {
                visible: !root.narrow
                x: 20
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6
                Rectangle {
                    width: 12
                    height: 1
                    color: "#b2b9e8"
                    anchors.verticalCenter: parent.verticalCenter
                }
                UiText { text: "程序路径"; color: Theme.muted; font.pixelSize: 10 }
                Item { width: 4; height: 1 }
                Row {
                    spacing: 2
                    anchors.verticalCenter: parent.verticalCenter
                    Repeater {
                        model: 3
                        Rectangle { width: 3; height: 1; color: "#7977b7" }
                    }
                }
                UiText { text: "快速移动"; color: Theme.muted; font.pixelSize: 10 }
            }
        }
    }

    Flickable {
        id: dro
        objectName: "droPanel"
        anchors.top: tabs.bottom
        anchors.bottom: parent.bottom
        width: parent.width
        visible: root.presentation.previewTab === "dro"
        contentWidth: width
        contentHeight: droContents.height + 48
        boundsBehavior: Flickable.StopAtBounds
        clip: true
        ScrollBar.vertical: UiScrollBar {}

        Column {
            id: droContents
            x: 24
            y: 24
            width: dro.width - 48
            Column {
                width: parent.width
                Repeater {
                    model: Catalog.axes
                    delegate: Item {
                        id: droLine
                        required property string modelData
                        width: droContents.width
                        height: (root.presentation.flags["show.large"] ? 46 : 36) * 1.7 + 1
                        Row {
                            spacing: 24
                            anchors.verticalCenter: parent.verticalCenter
                            UiText {
                                text: droLine.modelData + ":"
                                font.family: Theme.mono
                                font.pixelSize: root.presentation.flags["show.large"] ? 46 : 36
                            }
                            UiText {
                                objectName: "droCoordinate" + droLine.modelData
                                text: root.zero
                                font.family: Theme.mono
                                font.pixelSize: root.presentation.flags["show.large"] ? 46 : 36
                            }
                        }
                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 1
                            color: Theme.border
                        }
                    }
                }
            }
            Item { width: 1; height: 20 }
            Column {
                width: parent.width
                Repeater {
                    model: ["速度：0.000", "剩余行程：0.000", "",
                            "G54 工件坐标偏置", "X: 0.000", "Y: 0.000", "Z: 0.000", "",
                            "G92 临时坐标偏置", "X: 0.000   Y: 0.000   Z: 0.000", "",
                            "刀具长度补偿", "Z: 0.000", "坐标旋转角度：0.000"]
                    delegate: Item {
                        id: detail
                        required property string modelData
                        width: droContents.width
                        height: modelData === "" ? 33 : 23.4
                        UiText {
                            visible: detail.modelData !== ""
                            anchors.verticalCenter: parent.verticalCenter
                            text: detail.modelData
                            font.family: Theme.mono
                            font.pixelSize: 13
                            color: Theme.secondary
                        }
                        Rectangle {
                            visible: detail.modelData === ""
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width
                            height: 1
                            color: Theme.border
                        }
                    }
                }
            }
        }
    }
}
