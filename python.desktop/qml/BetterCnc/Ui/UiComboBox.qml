pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic

ComboBox {
    id: control
    property int optionHeight: 30
    implicitWidth: 150
    implicitHeight: Theme.controlHeight
    leftPadding: 8
    rightPadding: 23
    font.family: Theme.fontFamily
    font.pixelSize: 12
    hoverEnabled: true
    contentItem: UiText {
        text: control.displayText
        font: control.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: UiIcon {
        name: "chevron"
        rotation: 90
        width: 12
        height: 12
        x: control.width - width - 7
        y: (control.height - height) / 2
    }
    background: UiSurface {
        focusHighlighted: control.visualFocus
        pressed: control.down
        shadowStrength: control.enabled ? 1 : 0.35
        color: !control.enabled ? Theme.disabled : control.down || control.hovered ? Theme.hover : Theme.input
    }
    delegate: ItemDelegate {
        id: itemDelegate
        required property int index
        required property var modelData
        width: control.width
        height: control.optionHeight
        highlighted: control.highlightedIndex === index
        contentItem: UiText {
            text: control.textRole ? itemDelegate.modelData[control.textRole] : itemDelegate.modelData
            font: control.font
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle { color: itemDelegate.highlighted ? Theme.accentSoft : "transparent"; radius: 4 }
    }
    popup: Popup {
        enter: Transition { }
        exit: Transition { }
        y: control.height + 3
        width: control.width
        padding: 5
        implicitHeight: Math.min(contentItem.implicitHeight + 10, 300)
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollBar.vertical: UiScrollBar { }
        }
        background: UiSurface { shadowStrength: 2 }
    }
}
