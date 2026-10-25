import QtQuick
import QtQuick.Controls.Basic
import BetterCnc.Ui 1.0

// A touchscreen swipe must remain a scroll gesture, never an immediate jog.
Control {
    id: root
    property string text: ""
    property bool engaged: false
    readonly property bool down: engaged
    property bool touchArmed: false
    signal jogPressed()
    signal jogReleased()
    implicitWidth: 48
    implicitHeight: 44
    focusPolicy: Qt.TabFocus
    hoverEnabled: true
    Accessible.role: Accessible.Button
    Accessible.description: "鼠标按住点动；触屏保持 250 毫秒启动，松开或滑动停止"
    function beginJog() {
        if (!enabled || !visible || engaged || (Window.window && !Window.window.active)) return;
        forceActiveFocus(Qt.MouseFocusReason);
        engaged = true;
        jogPressed();
    }
    function endJog() {
        touchArmed = false;
        if (!engaged) return;
        engaged = false;
        jogReleased();
    }
    onEnabledChanged: if (!enabled) endJog()
    onVisibleChanged: if (!visible) endJog()
    onActiveFocusChanged: if (!activeFocus) endJog()
    Connections {
        target: root.Window.window
        function onActiveChanged() { if (!root.Window.window.active) root.endJog(); }
    }
    background: UiSurface {
        pressed: root.engaged || touchTap.pressed
        focusHighlighted: root.visualFocus
        shadowStrength: root.enabled ? 1 : 0.35
        color: !root.enabled ? Theme.disabled : root.engaged ? Theme.accentSoft : root.hovered || touchTap.pressed ? Theme.hover : Theme.surface
    }
    contentItem: UiText {
        text: root.text
        font.pixelSize: 22
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        color: !root.enabled ? Theme.muted : root.engaged ? Theme.accent : Theme.text
    }
    TapHandler {
        acceptedDevices: PointerDevice.Mouse
        acceptedButtons: Qt.LeftButton
        gesturePolicy: TapHandler.DragThreshold
        onPressedChanged: { if (pressed) root.beginJog(); else root.endJog(); }
        onCanceled: root.endJog()
    }
    TapHandler {
        id: touchTap
        acceptedDevices: PointerDevice.TouchScreen | PointerDevice.Stylus
        gesturePolicy: TapHandler.DragThreshold
        longPressThreshold: 0.25
        onLongPressed: if (root.touchArmed && root.activeFocus) root.beginJog()
        onPressedChanged: {
            if (pressed) {
                root.forceActiveFocus(Qt.MouseFocusReason);
                root.touchArmed = true;
            } else root.endJog();
        }
        onCanceled: root.endJog()
    }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Space || event.key === Qt.Key_Return) {
            if (!event.isAutoRepeat) beginJog();
            event.accepted = true;
        } else if (event.key === Qt.Key_Escape) {
            endJog();
            // Let the existing Escape shortcut also stop the program.
        }
    }
    Keys.onReleased: event => {
        if (event.key === Qt.Key_Space || event.key === Qt.Key_Return) {
            if (!event.isAutoRepeat) endJog();
            event.accepted = true;
        }
    }
    ToolTip.visible: hovered
    ToolTip.delay: 600
    ToolTip.text: Accessible.description
}
