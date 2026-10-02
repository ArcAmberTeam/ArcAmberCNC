import QtQuick
import QtTest
import BetterCnc.Catalog 1.0
import "../qml" as App

TestCase {
    id: testCase
    name: "WorkspaceParity"
    when: windowShown
    width: 1100
    height: 820
    property var window
    Component { id: appComponent; App.Main { } }
    SignalSpy { id: canvasPaint; signalName: "painted" }

    function visualChild(item, name) {
        if (item.objectName === name) return item;
        const children = item.children || [];
        for (let i = 0; i < children.length; ++i) {
            const found = visualChild(children[i], name);
            if (found) return found;
        }
        return null;
    }
    function control(name) {
        const result = findChild(window, name) || visualChild(window.contentItem, name);
        verify(result !== null, "Missing public UI: " + name);
        return result;
    }
    function init() {
        window = createTemporaryObject(appComponent, null);
        verify(window !== null);
        window.requestActivate();
        waitForRendering(window.contentItem);
        canvasPaint.target = control("toolpathCanvas");
        canvasPaint.clear();
        canvasPaint.target.requestPaint();
        canvasPaint.wait();
        waitForRendering(window.contentItem);
    }
    function cleanup() {
        if (window) window.close();
    }
    function click(name) {
        const item = control(name);
        mouseClick(item, item.width / 2, item.height / 2);
    }
    function test_initialLayout() {
        compare(control("workspace").width, 1100);
        compare(control("manualPanel").width, 296);
        compare(control("programSeparator").height, 7);
        compare(control("mdiTab").text, "手动输入 [F5]");
        compare(Catalog.sampleProgram.length, 200);
        compare(Catalog.toolbar.length, 19);
        verify(!control("dialogHost").visible);
        const picture = grabImage(window.contentItem);
        picture.save("workspace-default.png");
    }
    function test_manualAndMdi() {
        click("axisY");
        click("workTouchOff");
        const dialog = control("dialogHost");
        tryCompare(dialog, "visible", true);
        compare(dialog.axis, "Y");
        compare(dialog.actionId, "machine.touch-off");
        keyClick(Qt.Key_Escape);
        tryCompare(dialog, "visible", false);
        click("mdiTab");
        tryCompare(control("manualState"), "controlTab", "mdi");
        waitForRendering(control("mdiHistory"));
        click("mdiHistory1");
        compare(control("mdiCommand").text, "G0 Z10");
        click("mdiExecute");
        tryCompare(dialog, "visible", true);
        compare(dialog.actionId, "mdi.go");
        verify(dialog.description.indexOf("此操作不会执行") >= 0);
    }
    function test_machineChecksNeverToggle() {
        const item = control("mistCoolant");
        compare(item.checked, false);
        click("mistCoolant");
        tryCompare(control("dialogHost"), "visible", true);
        compare(item.checked, false);
    }
    function test_splitterKeyboardAndResize() {
        const sash = control("programSeparator");
        const workspace = control("workspace");
        sash.forceActiveFocus();
        keyClick(Qt.Key_Up);
        compare(workspace.programHeight, 194);
        for (let i = 0; i < 30; ++i) keyClick(Qt.Key_Up);
        compare(workspace.programHeight, 340);
        window.width = 760;
        window.height = 640;
        tryCompare(workspace, "width", 760);
        tryCompare(control("manualPanel"), "width", 264);
        compare(workspace.programHeight, workspace.maximumProgramHeight);
        const picture = grabImage(window.contentItem);
        picture.save("workspace-minimum.png");
    }
    function test_smallWindowSlidersStayReachableByKeyboard() {
        window.width = 760;
        window.height = 640;
        waitForRendering(window.contentItem);
        const slider = control("maxVelocity.slider");
        const scroller = control("manualScroller");
        slider.forceActiveFocus(Qt.TabFocusReason);
        tryVerify(() => slider.mapToItem(scroller, 0, 0).y >= 0);
        tryVerify(() => slider.mapToItem(scroller, 0, slider.height).y <= scroller.height);
        const previous = slider.value;
        keyClick(Qt.Key_Left);
        compare(slider.value, previous - 1);
        compare(control("coordinateX").text, "0.000");
        verify(!control("dialogHost").visible);
        const tab = control("manualTab");
        tab.forceActiveFocus(Qt.TabFocusReason);
        tryVerify(() => tab.mapToItem(scroller, 0, 0).y >= 0);
        tryVerify(() => tab.mapToItem(scroller, 0, tab.height).y <= scroller.height);
    }
    function test_keyboardFocusIsolation() {
        keyClick(Qt.Key_F5);
        compare(control("manualState").controlTab, "mdi");
        const input = control("mdiCommand");
        input.forceActiveFocus();
        keyClick(Qt.Key_X);
        keyClick(Qt.Key_V);
        keyClick(Qt.Key_D);
        compare(input.text.toLowerCase(), "xvd");
        compare(control("toolpathState").choices.view, "p");
        compare(control("toolpathState").rotate, false);
        keyClick(Qt.Key_F3);
        compare(control("manualState").controlTab, "manual");
    }
}
