pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import BetterCnc.Ui 1.0

Item {
    id: root
    property bool compact: false
    property var history: []
    property bool canOperate: false
    property bool commandAllowed: false
    signal commandRequested(string actionId, var payload)
    function executeMdi() {
        const command = mdiCommand.text.trim();
        if (canOperate && command) commandRequested("mdi.execute", {text: command});
    }
    readonly property int panelPadding: root.compact ? 12 : 18
    readonly property int verticalPadding: root.compact ? 12 : 16
    width: parent.width
    height: visible ? 270 + verticalPadding * 2 : 0


    Item {
        x: root.panelPadding
        y: root.verticalPadding
        width: parent.width - root.panelPadding * 2
        height: 270

        UiText {
            height: 18
            text: "历史指令："
            font.pixelSize: 12
            color: Theme.secondary
        }

        Rectangle {
            y: 26
            width: parent.width
            height: 160
            radius: 6
            color: Theme.input
            border.width: 1
            border.color: Theme.border

            ListView {
                id: historyList
                objectName: "mdiHistory"
                anchors.fill: parent
                anchors.margins: 6
                clip: true
                model: root.history
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: UiScrollBar {}
                Accessible.name: "手动输入历史"

                delegate: ItemDelegate {
                    id: historyButton
                    required property string modelData
                    required property int index
                    objectName: "mdiHistory" + index
                    width: historyList.width
                    height: 40
                    padding: 0
                    text: modelData
                    hoverEnabled: true

                    contentItem: UiText {
                        leftPadding: 6
                        rightPadding: 6
                        text: historyButton.text
                        font.family: Theme.mono
                        font.pixelSize: 12
                        color: historyButton.hovered || historyButton.visualFocus ? Theme.text : Theme.secondary
                        verticalAlignment: Text.AlignVCenter
                    }

                    background: Rectangle {
                        radius: 4
                        color: historyButton.hovered || historyButton.visualFocus ? Theme.accentSoft : "transparent"
                    }

                    onClicked: mdiCommand.text = modelData
                }
            }
        }

        UiText {
            y: 202
            height: 18
            text: "手动输入指令："
            font.pixelSize: 12
            color: Theme.secondary
        }

        RowLayout {
            y: 228
            width: parent.width
            height: 32
            spacing: 4

            UiTextField {
                id: mdiCommand
                objectName: "mdiCommand"
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.controlHeight
                font.family: Theme.mono
                Accessible.name: "手动输入指令："
                selectByMouse: true
                onAccepted: root.executeMdi()
            }

            UiButton {
                objectName: "mdiExecute"
                text: "执行"
                Layout.preferredWidth: 48
                Layout.preferredHeight: Theme.controlHeight
                enabled: root.canOperate && root.commandAllowed && mdiCommand.text.trim().length > 0
                onClicked: root.executeMdi()
            }
        }
    }
}
