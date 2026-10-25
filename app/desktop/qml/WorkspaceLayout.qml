import QtQuick

// Geometry contract for the two shells. No controller or presentation state.
QtObject {
    property real width: 0
    property real height: 0
    property int sidebarWidth: 304
    property int programHeight: 184
    property rect manualRect: Qt.rect(0, 0, 0, 0)
    property rect previewRect: Qt.rect(0, 0, 0, 0)
    property rect programRect: Qt.rect(0, 0, 0, 0)
    property rect guideRect: Qt.rect(0, 0, 0, 0)
    property bool manualVisible: true
    property bool previewVisible: true
    property bool programVisible: true
    property bool guideVisible: false
    property bool separatorVisible: false
}
