pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import BetterCnc.Ui 1.0
import BetterCnc.Catalog 1.0
import BetterCnc.Toolpath 1.0

Item {
    id: root
    required property ChromeActions actions
    required property ToolpathState preview
    property bool compact: width <= 900
    property string interfaceMode: "professional"
    property string guidedStage: "prepare"
    readonly property bool guided: interfaceMode === "guided"
    signal settingsRequested()
    function focusSettings() { settingsButton.forceActiveFocus(Qt.TabFocusReason); }
    signal stageRequested(string stage)
    readonly property bool menuOpen: {
        for (let index = 0; index < menubar.count; index++) {
            if (menubar.menuAt(index).visible) return true;
        }
        return false;
    }
    readonly property bool inlineNavigation: width >= 1000
    readonly property int headerInset: inlineNavigation ? 0 : 48
    implicitHeight: headerInset + 52 + context.height
    objectName: "workspace-chrome"
    readonly property var icons: ({
        "machine.estop": "octagon", "machine.power": "power", "file.open": "folder",
        "file.reload": "refresh", "program.run": "play", "program.step": "step",
        "program.pause": "pause", "program.stop": "stop", "program.block-delete": "skip",
        "program.optional": "circle", "view.zoom-in": "zoom-in", "view.zoom-out": "zoom-out",
        "view.z": "top", "view.z2": "diamond", "view.x": "side", "view.y": "front",
        "view.p": "cube", "view.rotate": "orbit", "view.clear": "eraser"
    })

    // At the target width, menus and settings share the action row.
    Rectangle {
        id: header
        z: 4
        width: parent.width
        height: root.inlineNavigation ? 52 : 48
        color: root.inlineNavigation ? "transparent" : Theme.sidebar
        UiDivider { anchors.bottom: parent.bottom; width: parent.width; height: 1; visible: !root.inlineNavigation }
        UiButton {
            id: settingsButton
            objectName: "open-settings"
            anchors.right: parent.right
            anchors.rightMargin: root.inlineNavigation ? 112 : 16
            anchors.verticalCenter: parent.verticalCenter
            width: 76; height: 44
            text: "设置"
            onClicked: root.settingsRequested()
        }
        MenuBar {
            id: menubar
            objectName: "main-menubar"
            x: root.inlineNavigation ? parent.width - 200 - width : 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            padding: 0
            background: Item { }
            delegate: MenuBarItem {
                id: trigger
                objectName: "menubar-" + text
                implicitHeight: 44
                implicitWidth: contentItem.implicitWidth + 20
                padding: 0
                contentItem: UiText {
                    text: trigger.text
                    font.pixelSize: 12
                    color: trigger.highlighted || trigger.hovered ? Theme.text : Theme.secondary
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 5
                    color: trigger.highlighted || trigger.hovered ? Theme.hover : "transparent"
                }
            }
            Instantiator {
                model: root.actions.menus
                delegate: MenuEntries {
                    required property var modelData
                    title: modelData.label
                    entries: modelData.children
                    actions: root.actions
                    objectName: "menu-" + modelData.id
                }
                onObjectAdded: function(index, object) { menubar.insertMenu(index, object); }
                onObjectRemoved: function(index, object) { menubar.removeMenu(object); }
            }
        }
    }
    Item {
        id: context
        y: root.headerInset + 52
        width: parent.width
        height: root.guided ? 44 : 0
        visible: root.guided
        UiDivider { anchors.bottom: parent.bottom; width: parent.width; height: 1 }
        Row {
            visible: root.guided
            x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 4
            Repeater {
                model: [{id: "prepare", label: "1  准备程序"}, {id: "preview", label: "2  检查刀路"}, {id: "device", label: "3  设备控制"}]
                UiButton {
                    required property var modelData
                    objectName: "stage-" + modelData.id
                    text: modelData.label
                    kind: "tab"; height: 44; width: root.compact ? 100 : 124
                    selected: root.guidedStage === modelData.id
                    onClicked: root.stageRequested(modelData.id)
                }
            }
        }
    }
    Item {
        y: root.headerInset
        width: parent.width
        height: 52
        UiDivider { anchors.bottom: parent.bottom; width: parent.width; height: 1 }
        Rectangle {
            anchors.right: parent.right
            width: 112; height: parent.height
            color: Theme.base; z: 2
        }
        UiButton {
            z: 3
            objectName: "toolbar-program.stop"
            anchors.right: parent.right
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            width: 88
            text: "停止"; iconName: "stop"; kind: "danger"
            tooltip: "停止程序 [Esc]"
            enabled: root.actions.canActivate("program.stop")
            onClicked: root.actions.activate("program.stop")
        }
        Flickable {
            id: toolbarViewport
            objectName: "toolbar-viewport"
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: root.inlineNavigation ? 216 + menubar.width : 112
            contentWidth: toolbarRow.width
            contentHeight: height
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.HorizontalFlick
            function ensureVisible(item: Item): void {
                const left = item.mapToItem(toolbarRow, 0, 0).x;
                const right = left + item.width;
                const target = left < contentX ? left
                             : right > contentX + width ? right - width : contentX;
                contentX = Math.max(0, Math.min(contentWidth - width, target));
            }
            Row {
                id: toolbarRow
                y: 6
                height: 40
                spacing: 4
                Repeater {
                    model: Catalog.toolbar.filter(entry => entry.id !== "program.stop"
                        && !entry.id.startsWith("view.") && entry.id !== "program.optional" && entry.id !== "program.block-delete"
                        && (!root.guided || ["machine.estop", "machine.power", "file.open", "program.run", "program.pause"].indexOf(entry.id) >= 0))
                    delegate: Row {
                        id: toolbarEntry
                        required property var modelData
                        spacing: 4
                        height: 40
                        Item {
                            visible: !!toolbarEntry.modelData.separator
                            width: visible ? 11 : 0
                            height: 40
                            Rectangle { anchors.centerIn: parent; width: 1; height: 18; color: Theme.borderControl }
                        }
                        UiButton {
                            id: toolbarButton
                            objectName: "toolbar-" + toolbarEntry.modelData.id
                            width: root.guided ? 88 : toolbarEntry.modelData.id === "machine.estop" ? 76 : toolbarEntry.modelData.id === "program.run" ? 80 : 36
                            height: 40
                            kind: toolbarEntry.modelData.id === "machine.estop" ? "danger" : toolbarEntry.modelData.id === "program.run" ? "primary" : "toolbar"
                            iconName: actionId === "program.resume" ? "play" : root.icons[toolbarEntry.modelData.id] || "cube"
                            text: root.guided ? ({"machine.estop": "急停", "machine.power": "电源", "file.open": "打开", "program.run": "运行", "program.pause": root.actions.machine.paused ? "继续" : "暂停"})[toolbarEntry.modelData.id]
                                  : toolbarEntry.modelData.id === "machine.estop" ? "急停" : toolbarEntry.modelData.id === "program.run" ? "运行" : ""
                            font.pixelSize: Theme.labelSize
                            selected: toolbarEntry.modelData.id === "view." + root.preview.choices.view
                                      || (toolbarEntry.modelData.id === "view.rotate" && root.preview.rotate)
                                      || (toolbarEntry.modelData.id === "machine.power" && !!root.actions.machine.powered)
                                      || (toolbarEntry.modelData.id === "program.optional" && !!root.actions.machine.optionalStop)
                                      || (toolbarEntry.modelData.id === "program.block-delete" && !!root.actions.machine.blockDelete)
                            readonly property string actionId: root.guided && toolbarEntry.modelData.id === "program.pause" && root.actions.machine.paused ? "program.resume" : toolbarEntry.modelData.id
                            enabled: root.actions.canActivate(actionId)
                            tooltip: actionId === "program.resume" ? "继续程序" : toolbarEntry.modelData.label
                            onActiveFocusChanged: {
                                if (activeFocus) toolbarViewport.ensureVisible(toolbarButton);
                            }
                            onClicked: root.actions.activate(actionId, toolbarEntry.modelData.label)
                        }
                    }
                }
            }
        }
    }
}
