pragma ComponentBehavior: Bound
import QtQuick

// Small translucent steps keep the shadow available on the software renderer.
Rectangle {
    id: root
    property bool elevated: true
    property bool pressed: false
    property bool focusHighlighted: false
    property real shadowStrength: 1
    radius: Theme.controlRadius
    color: Theme.surface
    border.width: 0

    Repeater {
        model: 5
        Rectangle {
            required property int index
            z: -1
            x: -index - 1
            y: -index + (root.pressed ? 0 : 1)
            width: root.width + 2 * (index + 1)
            height: root.height + 2 * (index + 1)
            radius: root.radius + index + 1
            visible: root.elevated || root.focusHighlighted
            color: root.focusHighlighted ? Theme.accent : Theme.shadow
            opacity: (root.focusHighlighted ? 0.055 : 0.018)
                * (5 - index) / 5 * root.shadowStrength * (root.pressed ? 0.4 : 1)
        }
    }
}
