import QtQuick
import BetterCnc.Ui 1.0

// QtDragon-inspired: persistent manual controls, preview/DRO above the program.
WorkspaceLayout {
    readonly property real contentX: sidebarWidth + Theme.gap
    readonly property real contentWidth: width - contentX
    manualRect: Qt.rect(0, 0, sidebarWidth, height)
    previewRect: Qt.rect(contentX, 0, contentWidth, height - programHeight - 7)
    programRect: Qt.rect(contentX, height - programHeight, contentWidth, programHeight)
    separatorVisible: true
}
