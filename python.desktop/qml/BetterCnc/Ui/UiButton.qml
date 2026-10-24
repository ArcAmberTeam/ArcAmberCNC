import QtQuick
import QtQuick.Controls.Basic

Button {
    id: control
    property string iconName: ""
    property bool selected: false
    property string kind: "normal"
    property string tooltip: ""
    readonly property color foreground: !enabled ? Theme.muted
        : kind === "danger" ? Theme.danger
        : selected ? Theme.accent
        : kind === "tab" && !selected || kind === "toolbar" && !hovered ? Theme.secondary : Theme.text
    implicitWidth: Math.max(36, implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: kind === "primary" || kind === "danger" ? 40 : Theme.controlHeight
    padding: 4
    leftPadding: kind === "toolbar" ? 5 : 10
    rightPadding: leftPadding
    spacing: 7
    font.family: Theme.fontFamily
    font.pixelSize: Theme.bodySize
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    opacity: 1
    contentItem: Item {
        implicitWidth: contentRow.implicitWidth
        implicitHeight: contentRow.implicitHeight
        Row {
            id: contentRow
            spacing: control.iconName && control.text ? control.spacing : 0
            anchors.centerIn: parent
            UiIcon {
                visible: control.iconName !== ""
                name: control.iconName
                color: control.foreground
                anchors.verticalCenter: parent.verticalCenter
            }
            UiText {
                visible: control.text !== ""
                text: control.text
                color: control.foreground
                font: control.font
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
    background: Rectangle {
        radius: Theme.controlRadius
        color: !control.enabled ? Theme.disabled
            : control.kind === "danger" ? (control.hovered || control.down ? Theme.dangerSoft : Theme.surface)
            : control.kind === "primary" ? (control.down ? Theme.accentPressed : control.hovered ? Theme.accentHover : Theme.accentFill)
            : control.selected || control.down ? Theme.accentSoft
            : control.hovered ? Theme.hover
            : control.kind === "toolbar" || control.kind === "tab" ? "transparent" : Theme.raised
        border.width: 1
        border.color: control.kind === "danger" ? Theme.danger
            : control.kind === "primary" ? Theme.accent
            : control.selected || control.down ? (control.kind === "tab" ? Theme.border : Theme.accent)
            : control.kind === "toolbar" || control.kind === "tab" ? "transparent"
            : control.hovered ? Theme.borderControl : Theme.borderControl
        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            visible: control.visualFocus
            color: "transparent"
            border.color: Theme.accent
            border.width: 2
            radius: 8
        }
    }
    ToolTip.visible: hovered && tooltip.length > 0
    ToolTip.text: tooltip
    ToolTip.delay: 600
    Accessible.name: tooltip || text
}
