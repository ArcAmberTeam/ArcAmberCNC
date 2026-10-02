pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import BetterCnc.Ui 1.0
import BetterCnc.Manual 1.0
import BetterCnc.Toolpath 1.0
import BetterCnc.Program 1.0
import BetterCnc.Chrome 1.0

Rectangle {
    id: workspace
    objectName: "workspace"
    color: Theme.base
    property Item focusedItem: null
    property int programHeight: 184
    property bool initialized: false
    readonly property int maximumProgramHeight: Math.max(90, Math.min(340, panes.height - 247))
    readonly property bool compact: width <= 900
    readonly property int sidebarWidth: compact ? 264 : 296
    readonly property bool viewShortcutsEnabled: !dialogs.visible && !chrome.menuOpen && !editing()

    function editing() {
        let item = focusedItem;
        while (item) {
            if (item instanceof TextInput || item instanceof TextEdit || item instanceof ComboBox)
                return true;
            item = item.parent;
        }
        return false;
    }
    function setProgramHeight(value) {
        programHeight = Math.round(Math.max(90, Math.min(maximumProgramHeight, value)));
    }
    onMaximumProgramHeightChanged: if (initialized) setProgramHeight(programHeight)
    Component.onCompleted: {
        initialized = true;
        setProgramHeight(programHeight);
    }

    ManualState { id: manualPresentation; objectName: "manualState" }
    ToolpathState { id: toolpathPresentation; objectName: "toolpathState" }
    ChromeActions {
        id: chromeActions
        manual: manualPresentation
        preview: toolpathPresentation
        onDialogRequested: (actionId, title, axis) => dialogs.openDialog(actionId, title, axis)
    }
    ChromeBar {
        id: chrome
        width: parent.width
        height: 146
        compact: workspace.compact
        actions: chromeActions
        preview: toolpathPresentation
    }
    Item {
        id: panes
        y: 146
        width: parent.width
        height: parent.height - y
        ManualPanel {
            width: workspace.sidebarWidth
            height: parent.height
            presentation: manualPresentation
            compact: workspace.compact
            onDialogRequested: (actionId, title, axis) => dialogs.openDialog(actionId, title, axis)
        }
        ToolpathPanel {
            x: workspace.sidebarWidth
            width: parent.width - x
            height: parent.height - workspace.programHeight - 7
            presentation: toolpathPresentation
            compact: workspace.width <= 1100
        }
        Rectangle {
            id: sash
            objectName: "programSeparator"
            x: workspace.sidebarWidth
            y: parent.height - workspace.programHeight - height
            width: parent.width - x
            height: 7
            color: Theme.base
            activeFocusOnTab: true
            Accessible.role: Accessible.Grip
            Accessible.name: "调整程序区高度"
            Rectangle { width: parent.width; height: 1; color: Theme.border }
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 2
                width: 26
                height: 2
                radius: 2
                color: sashMouse.containsMouse ? Theme.accent : "#41434c"
            }
            Rectangle { anchors.fill: parent; color: "transparent"; border.width: 2; border.color: Theme.accent; visible: sash.activeFocus }
            MouseArea {
                id: sashMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.SizeVerCursor
                preventStealing: true
                onPressed: sash.forceActiveFocus(Qt.MouseFocusReason)
                onPositionChanged: mouse => {
                    if (pressed) {
                        const point = mapToItem(panes, mouse.x, mouse.y);
                        workspace.setProgramHeight(panes.height - point.y);
                    }
                }
            }
            Keys.onUpPressed: workspace.setProgramHeight(workspace.programHeight + 10)
            Keys.onDownPressed: workspace.setProgramHeight(workspace.programHeight - 10)
        }
        ProgramPanel {
            x: workspace.sidebarWidth
            y: parent.height - workspace.programHeight
            width: parent.width - x
            height: workspace.programHeight
            onDialogRequested: (actionId, title, axis) => dialogs.openDialog(actionId, title, axis)
        }
    }
    DialogHost { id: dialogs; objectName: "dialogHost" }
    Shortcut { sequence: "F3"; enabled: !dialogs.visible; onActivated: manualPresentation.controlTab = "manual" }
    Shortcut { sequence: "F5"; enabled: !dialogs.visible; onActivated: manualPresentation.controlTab = "mdi" }
    Repeater {
        model: ["X", "Y", "Z"]
        delegate: Item {
            id: axisShortcut
            required property string modelData
            Shortcut {
                sequence: axisShortcut.modelData
                enabled: workspace.viewShortcutsEnabled
                onActivated: manualPresentation.selectedAxis = axisShortcut.modelData
            }
        }
    }
    Shortcut {
        sequence: "V"
        enabled: workspace.viewShortcutsEnabled
        onActivated: {
            const views = ["p", "z", "z2", "x", "y"];
            toolpathPresentation.setChoice("view", views[(views.indexOf(toolpathPresentation.choices.view) + 1) % views.length]);
        }
    }
    Shortcut { sequence: "D"; enabled: workspace.viewShortcutsEnabled; onActivated: toolpathPresentation.rotate = !toolpathPresentation.rotate }
    Shortcut { sequence: "!"; enabled: workspace.viewShortcutsEnabled; onActivated: toolpathPresentation.setChoice("units", toolpathPresentation.choices.units === "mm" ? "inch" : "mm") }
    Shortcut { sequence: "@"; enabled: workspace.viewShortcutsEnabled; onActivated: toolpathPresentation.setChoice("position", toolpathPresentation.choices.position === "actual" ? "commanded" : "actual") }
    Shortcut { sequence: "#"; enabled: workspace.viewShortcutsEnabled; onActivated: toolpathPresentation.setChoice("coordinates", toolpathPresentation.choices.coordinates === "relative" ? "machine" : "relative") }
}
