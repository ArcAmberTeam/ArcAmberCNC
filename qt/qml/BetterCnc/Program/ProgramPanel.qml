pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import BetterCnc.Ui 1.0
import BetterCnc.Catalog 1.0

FocusScope {
    id: root
    objectName: "programPanel"
    property int selectedLine: 0
    property bool showFocusRing: false
    signal dialogRequested(string actionId, string title, string axis)
    clip: true
    activeFocusOnTab: true
    Accessible.role: Accessible.List
    Accessible.name: "加工程序"
    onActiveFocusChanged: showFocusRing = activeFocus

    function selectLine(line: int): void {
        selectedLine = Math.max(0, Math.min(Catalog.sampleProgram.length - 1, line));
    }

    function openMenu(x: real, y: real): void {
        forceActiveFocus();
        contextMenu.popup(root, x, y);
    }

    Keys.onDownPressed: {
        showFocusRing = true;
        selectLine(selectedLine + 1);
    }
    Keys.onUpPressed: {
        showFocusRing = true;
        selectLine(selectedLine - 1);
    }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Menu || (event.key === Qt.Key_F10 && (event.modifiers & Qt.ShiftModifier))) {
            openMenu(65, Math.max(44, Math.min(height - 40, 44 + selectedLine * 24 - lines.contentY)));
            event.accepted = true;
        }
    }

    Rectangle { anchors.fill: parent; color: Theme.base }
    ListView {
        id: lines
        objectName: "programLines"
        anchors.top: heading.bottom
        anchors.bottom: parent.bottom
        width: parent.width
        model: Catalog.sampleProgram
        currentIndex: root.selectedLine
        topMargin: 6
        bottomMargin: 6
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.HorizontalAndVerticalFlick
        contentWidth: Math.max(width, longestLine.advanceWidth + 79)
        clip: true
        keyNavigationEnabled: false
        highlightFollowsCurrentItem: false
        ScrollBar.vertical: UiScrollBar {}
        ScrollBar.horizontal: UiScrollBar {}

        TextMetrics {
            id: longestLine
            text: Catalog.sampleProgram.reduce((longest, line) => line.length > longest.length ? line : longest, "")
            font.family: Theme.mono
            font.pixelSize: 12
        }
        delegate: Rectangle {
            id: programLine
            required property string modelData
            required property int index
            objectName: "programLine" + index
            width: lines.contentWidth
            height: 24
            color: rowMouse.containsMouse ? "#202126" : (index === root.selectedLine ? "#22232c" : "transparent")
            Accessible.role: Accessible.ListItem
            Accessible.name: (index + 1) + " " + modelData
            Accessible.selected: index === root.selectedLine

            Rectangle {
                width: 2
                height: parent.height
                color: programLine.index === root.selectedLine ? Theme.accent : "transparent"
            }
            UiText {
                x: 5
                width: 32
                height: 24
                text: programLine.index + 1
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
                color: programLine.index === root.selectedLine ? "#c6c0ff" : Theme.muted
                font.family: Theme.mono
                font.pixelSize: 12
            }
            UiText {
                x: 57
                height: 24
                text: programLine.modelData || " "
                textFormat: Text.PlainText
                verticalAlignment: Text.AlignVCenter
                color: /^\s*\(/.test(programLine.modelData) ? "#9599a5" : "#c3baff"
                font.family: Theme.mono
                font.pixelSize: 12
            }
            MouseArea {
                id: rowMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.IBeamCursor
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                onPressed: mouse => {
                    root.forceActiveFocus();
                    root.showFocusRing = false;
                    root.selectLine(programLine.index);
                    if (mouse.button === Qt.RightButton) {
                        const point = mapToItem(root, mouse.x, mouse.y);
                        root.openMenu(point.x, point.y);
                    }
                }
            }
        }
    }

    Rectangle {
        id: heading
        width: parent.width
        height: 38
        color: Theme.base
        Row {
            x: 18
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            UiIcon {
                name: "file"
                width: 14
                height: 14
                color: Theme.secondary
                anchors.verticalCenter: parent.verticalCenter
            }
            UiText { text: "加工程序"; font.pixelSize: 11 }
            UiText {
                leftPadding: 8
                text: Catalog.fixture.fileName
                color: Theme.muted
                font.family: Theme.mono
                font.pixelSize: 11
            }
        }
        UiText {
            anchors.right: parent.right
            anchors.rightMargin: 18
            anchors.verticalCenter: parent.verticalCenter
            text: Catalog.sampleProgram.length + " 行"
            font.pixelSize: 10
            color: Theme.muted
        }
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: Theme.border
        }
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onClicked: mouse => {
                root.forceActiveFocus();
                root.showFocusRing = false;
                if (mouse.button === Qt.RightButton)
                    root.openMenu(mouse.x, mouse.y);
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        color: "transparent"
        border.width: 2
        border.color: Theme.accent
        visible: root.activeFocus && root.showFocusRing
    }

    Menu {
        id: contextMenu
        objectName: "programContextMenu"
        width: 220
        padding: 5
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle {
            color: "#202125"
            border.color: Theme.borderControl
            border.width: 1
            radius: 9
        }
        MenuItem {
            id: programMenuLabel
            text: "加工程序"
            enabled: false
            height: 30
            leftPadding: 5
            contentItem: UiText {
                text: programMenuLabel.text
                font.pixelSize: 12
                color: Theme.muted
                verticalAlignment: Text.AlignVCenter
            }
            background: Item {}
        }
        MenuSeparator {
            height: 11
            contentItem: Rectangle { implicitHeight: 1; color: Theme.borderControl }
            leftPadding: 5
            rightPadding: 5
            topPadding: 5
            bottomPadding: 5
        }
        MenuItem {
            id: runLineItem
            objectName: "runFromLineAction"
            text: "从此行运行"
            height: 30
            leftPadding: 5
            contentItem: UiText {
                text: runLineItem.text
                font.pixelSize: 12
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                radius: 5
                color: runLineItem.highlighted ? "#34353c" : "transparent"
            }
            onTriggered: root.dialogRequested("program.run-line", "从此行运行", "")
        }
    }
}
