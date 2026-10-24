import QtQuick
import QtQuick.Controls.Basic

TextField {
    id: control
    implicitWidth: 130
    implicitHeight: Theme.controlHeight
    padding: 8
    topPadding: 4
    bottomPadding: 4
    color: Theme.text
    selectionColor: Theme.accentSoft
    selectedTextColor: Theme.text
    placeholderTextColor: Theme.muted
    font.family: Theme.fontFamily
    font.pixelSize: Theme.bodySize
    renderType: Text.NativeRendering
    background: Rectangle {
        radius: Theme.controlRadius
        color: control.enabled ? Theme.input : Theme.disabled
        border.color: control.activeFocus ? Theme.accent : Theme.borderControl
        border.width: control.activeFocus ? 2 : 1
    }
}
