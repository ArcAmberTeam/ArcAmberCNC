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
    background: UiSurface {
        elevated: control.kind !== "tab" || control.selected || control.hovered
        pressed: control.down
        focusHighlighted: control.visualFocus
        shadowStrength: control.enabled ? 1 : 0.35
        color: !control.enabled ? Theme.disabled
            : control.kind === "danger" ? (control.hovered || control.down ? Theme.dangerSoft : Theme.surface)
            : control.kind === "primary" ? (control.down ? Theme.accentPressed : control.hovered ? Theme.accentHover : Theme.accentFill)
            : control.selected || control.down ? Theme.accentSoft
            : control.hovered ? Theme.hover
            : control.kind === "tab" ? "transparent" : Theme.raised
    }
    ToolTip.visible: hovered && tooltip.length > 0
    ToolTip.text: tooltip
    ToolTip.delay: 600
    Accessible.name: tooltip || text
}
