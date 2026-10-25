import QtQuick
import QtTest
import "../qml" as App

TestCase {
    name: "KioskStatus"
    when: windowShown
    Component { id: statusComponent; App.KioskStatus { } }

    function test_read_only_background_cannot_take_focus_or_close() {
        const window = createTemporaryObject(statusComponent, null, {
            statusModel: {headline: "CNC 尚未就绪", message: "请联系维护人员查看启动日志。"}
        });
        verify(window !== null);
        verify((window.flags & Qt.WindowDoesNotAcceptFocus) !== 0);
        verify((window.flags & Qt.WindowTransparentForInput) !== 0);
        verify((window.flags & Qt.WindowStaysOnBottomHint) !== 0);
        compare(window.close(), false);
        compare(window.visible, true);
        compare(window.activeFocusItem, null);
    }
}
