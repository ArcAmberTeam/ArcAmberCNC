import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import BetterCnc.Ui 1.0

Window {
    id: statusWindow
    objectName: "kioskStatusWindow"
    property var statusModel: null
    width: Screen.width
    height: Screen.height
    x: Screen.virtualX
    y: Screen.virtualY
    color: Theme.base
    visible: true
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus
           | Qt.WindowTransparentForInput | Qt.X11BypassWindowManagerHint
           | Qt.WindowStaysOnBottomHint
    onClosing: function(close) { close.accepted = false; }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(640, statusWindow.width - 64)
        spacing: 24
        UiText {
            Layout.fillWidth: true
            text: statusWindow.statusModel ? statusWindow.statusModel.headline : "CNC 正在启动"
            font.pixelSize: 32
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
        }
        UiText {
            Layout.fillWidth: true
            text: statusWindow.statusModel ? statusWindow.statusModel.message : "正在等待控制服务和机床硬件就绪。"
            color: Theme.secondary
            font.pixelSize: 18
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
        }
    }
}
