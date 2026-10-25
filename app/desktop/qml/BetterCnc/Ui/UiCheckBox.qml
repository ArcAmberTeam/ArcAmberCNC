import QtQuick
import QtQuick.Controls.Basic

CheckBox {
    id: control
    property bool interactive: true
    implicitHeight: 27
    implicitWidth: implicitContentWidth + 21
    padding: 0
    spacing: 7
    font.family: Theme.fontFamily
    font.pixelSize: Theme.labelSize
    hoverEnabled: true
    nextCheckState: function() { return interactive ? (checked ? Qt.Unchecked : Qt.Checked) : checkState; }
    indicator: UiSurface {
        x: 0
        y: (control.height - height) / 2
        width: 14
        height: 14
        radius: 3
        color: !control.enabled ? Theme.disabled : control.checked ? Theme.accentFill : Theme.hover
        focusHighlighted: control.visualFocus
        pressed: control.down
        shadowStrength: control.enabled ? 1 : 0.35
        UiText {
            anchors.centerIn: parent
            text: control.checked ? "✓" : ""
            font.pixelSize: 12
        }
    }
    contentItem: UiText {
        text: control.text
        font: control.font
        color: Theme.secondary
        leftPadding: 21
        verticalAlignment: Text.AlignVCenter
    }
}
