import QtQuick
import QtQuick.Controls.Basic

Item {
    id: root
    property string label: ""
    property string unit: "%"
    property bool valueKnown: true
    property real from: 0
    property real to: 100
    property alias value: slider.value
    signal moved(real value)
    implicitWidth: 250
    implicitHeight: 49
    UiText { text: root.label; color: Theme.secondary; font.pixelSize: 12; y: 0 }
    Row {
        anchors.right: parent.right
        spacing: 5
        UiText { objectName: root.objectName + ".value"; text: root.valueKnown ? Math.round(slider.value) : "—"; font.family: Theme.mono; font.pixelSize: 12 }
        UiText { visible: root.valueKnown; text: root.unit; color: Theme.secondary; font.pixelSize: Theme.labelSize; anchors.baseline: parent.children[0].baseline }
    }
    Slider {
        id: slider
        objectName: root.objectName + ".slider"
        y: 23
        width: parent.width
        height: 24
        padding: 0
        from: root.from
        to: root.to
        value: 100
        stepSize: 1
        focusPolicy: Qt.StrongFocus
        onMoved: root.moved(value)
        Accessible.name: root.label
        background: Rectangle {
            x: slider.leftPadding
            y: slider.topPadding + slider.availableHeight / 2 - height / 2
            width: slider.availableWidth
            height: 4
            radius: 3
            color: Theme.borderControl
            Rectangle { width: slider.visualPosition * parent.width; height: 4; radius: 3; color: Theme.accentFill }
        }
        handle: Rectangle {
            x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
            y: slider.topPadding + slider.availableHeight / 2 - height / 2
            width: 14
            height: 14
            radius: 6
            color: Theme.surface
            border.width: 2
            border.color: Theme.accent
            Rectangle {
                anchors.fill: parent
                anchors.margins: -3
                visible: slider.visualFocus
                color: "transparent"
                radius: 8
                border.color: Theme.accent
                border.width: 2
            }
        }
    }
}
