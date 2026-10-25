pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import BetterCnc.Ui 1.0

ApplicationWindow {
    id: root
    required property var backend
    required property var testedWindow
    title: "外部注入测试控制台 · 无硬件"
    width: 620; height: 390; minimumWidth: 620; minimumHeight: 390
    visible: true
    color: Theme.base
    Column {
        x: 20; y: 20; width: parent.width - 40; spacing: 16
        UiText { text: "LinuxCNC 外部接口模拟"; font.pixelSize: Theme.titleSize; font.weight: Font.DemiBold }
        UiText {
            width: parent.width; wrapMode: Text.Wrap; color: Theme.secondary
            text: "原始 GUI → 原始桌面后端 → Unix socket → 原始控制服务 → 接口替身。先在主窗口解除急停、上电、全部回零，再运行。"
        }
        UiText {
            objectName: "simulation-status"
            text: root.backend.simulationStatus + "  ·  进度 " + Math.round(root.backend.progress * 100) + "%  ·  行 " + (root.backend.snapshot.currentLine || 0)
            Accessible.role: Accessible.StaticText
            Accessible.name: "模拟状态 " + text
        }
        UiText {
            text: "XYZ  " + (root.backend.snapshot.actualPosition || []).slice(0, 3).map(v => Number(v).toFixed(3)).join("  ") + " mm"
            font.family: Theme.mono
        }
        Row {
            spacing: 12
            UiText { text: "播放速度"; color: Theme.secondary; anchors.verticalCenter: parent.verticalCenter }
            UiComboBox {
                objectName: "simulation-rate"; width: 100
                model: ["1×", "2×", "5×", "10×"]
                onActivated: root.backend.setPlaybackRate([1, 2, 5, 10][currentIndex])
            }
            UiButton {
                text: "显示主窗口"
                onClicked: { root.testedWindow.showNormal(); root.testedWindow.raise(); root.testedWindow.requestActivate() }
            }
        }
        Row {
            spacing: 12
            UiButton { text: "注入外部急停"; onClicked: root.backend.emergencyStop() }
            UiButton { text: root.backend.available ? "断开 NML" : "恢复 NML"; onClicked: root.backend.toggleConnection() }
            UiButton { text: "注入驱动报警"; onClicked: root.backend.driveAlarm() }
        }
        UiText { text: "接口行为测试 · 无真实 LinuxCNC / HAL / 硬件\n仅支持受限 G0/G1；无碰撞、切削或实时运动验证"; color: Theme.accent; font.pixelSize: Theme.labelSize }
    }
}
