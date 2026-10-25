import QtQuick

Rectangle {
    id: root
    property bool vertical: false
    implicitWidth: vertical ? 1 : 0
    implicitHeight: vertical ? 0 : 1
    color: Theme.border
    Rectangle {
        x: root.vertical ? root.width : 0
        y: root.vertical ? 0 : root.height
        width: root.vertical ? 2 : root.width
        height: root.vertical ? root.height : 2
        color: Theme.separatorShadow
    }
}
