import QtQuick
import BetterCnc.Ui 1.0

// Stage navigation changes geometry/visibility; panel instances stay alive.
WorkspaceLayout {
    property string stage: "prepare"
    readonly property bool wide: width >= 1264
    readonly property real mainWidth: width - sidebarWidth - Theme.gap
    manualVisible: stage === "device"
    guideVisible: !manualVisible
    programVisible: stage === "prepare"
    previewVisible: stage !== "prepare" || wide
    manualRect: Qt.rect(width - sidebarWidth, 0, sidebarWidth, height)
    guideRect: manualRect
    programRect: Qt.rect(0, 0, wide ? 280 : mainWidth, height)
    previewRect: Qt.rect(stage === "prepare" ? 280 + Theme.gap : 0, 0,
                         mainWidth - (stage === "prepare" ? 280 + Theme.gap : 0), height)
}
