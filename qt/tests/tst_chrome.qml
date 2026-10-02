import QtQuick
import QtTest
import BetterCnc.Catalog 1.0
import "../qml" as App

TestCase {
    id: testCase
    name: "ChromeParity"
    when: windowShown
    width: 1100
    height: 820
    property var window
    Component { id: appComponent; App.Main { } }

    function findVisual(item, name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        for (const child of item.children || []) {
            const result = findVisual(child, name);
            if (result) return result;
        }
        return null;
    }
    function control(name) {
        const result = findChild(window, name) || findVisual(window.contentItem, name);
        verify(result !== null, "Missing public UI: " + name);
        return result;
    }
    function init() {
        window = createTemporaryObject(appComponent, null);
        verify(window !== null);
        window.requestActivate();
        waitForRendering(window.contentItem);
    }
    function cleanup() {
        if (window) window.close();
    }
    function click(item) {
        mouseClick(item, item.width / 2, item.height / 2);
    }
    function leafEntries() {
        const result = [];
        function visit(entries, path) {
            entries.forEach((entry, index) => {
                const nextPath = path.concat(index);
                if (entry.children) visit(entry.children, nextPath);
                else if (entry.kind !== "separator") result.push({ tag: entry.id, entry: entry, path: nextPath });
            });
        }
        visit(Catalog.menus, []);
        return result;
    }

    function test_allMenuEntries_data() { return leafEntries(); }
    function test_allMenuEntries(data) {
        const beforeFlag = control("toolpathState").flags[data.entry.id];
        const menubar = control("main-menubar");
        click(menubar.itemAt(data.path[0]));
        let menu = menubar.menuAt(data.path[0]);
        tryCompare(menu, "visible", true);
        for (let depth = 1; depth < data.path.length; depth++) {
            const index = data.path[depth];
            menu.contentItem.positionViewAtIndex(index, ListView.Contain);
            waitForRendering(window.contentItem);
            const item = menu.itemAt(index);
            verify(item !== null);
            if (depth < data.path.length - 1) {
                click(item);
                menu = item.subMenu;
                tryCompare(menu, "visible", true);
            } else {
                click(item);
            }
        }
        const entry = data.entry;
        const manual = control("manualState");
        const preview = control("toolpathState");
        const dialog = control("dialogHost");
        if (entry.kind === "radio") {
            const actual = entry.group === "mode" ? manual.mode : entry.group === "touch" ? manual.touchTarget : preview.choices[entry.group];
            compare(actual, entry.value);
            verify(!dialog.visible);
        } else if (entry.kind === "check" && entry.id in preview.flags) {
            compare(preview.flags[entry.id], !beforeFlag);
            verify(!dialog.visible);
        } else if (entry.id === "view.clear") {
            compare(preview.flags["show.live"], false);
            verify(!dialog.visible);
        } else {
            tryCompare(dialog, "visible", true);
            compare(dialog.actionId, entry.id);
            if (entry.id.indexOf("help.") !== 0 && entry.id !== "file.properties")
                verify(dialog.description.indexOf("此操作不会执行") >= 0);
        }
        // No menu entry changes any sample machine state.
        compare(Catalog.fixture.taskState, "急停");
    }

    function test_toolbar_data() {
        return Catalog.toolbar.map(entry => ({ tag: entry.id, entry: entry }));
    }
    function test_toolbar(data) {
        const preview = control("toolpathState");
        const beforeZoom = preview.zoom;
        click(control("toolbar-" + data.entry.id));
        const id = data.entry.id;
        const dialog = control("dialogHost");
        if (id === "view.zoom-in") verify(preview.zoom > beforeZoom);
        else if (id === "view.zoom-out") verify(preview.zoom < beforeZoom);
        else if (id === "view.rotate") compare(preview.rotate, true);
        else if (id === "view.clear") compare(preview.flags["show.live"], false);
        else if (id.indexOf("view.") === 0) compare(preview.choices.view, id.slice(5));
        else {
            tryCompare(dialog, "visible", true);
            compare(dialog.actionId, id);
        }
    }

    function test_menuAndDialogFocus() {
        const menubar = control("main-menubar");
        const chrome = control("workspace-chrome");
        click(menubar.itemAt(2));
        tryCompare(chrome, "menuOpen", true);
        keyClick(Qt.Key_V);
        compare(control("toolpathState").choices.view, "p");
        keyClick(Qt.Key_Escape);
        tryCompare(chrome, "menuOpen", false);
        keyClick(Qt.Key_V);
        compare(control("toolpathState").choices.view, "z");
        const emergencyStop = control("toolbar-machine.estop");
        click(emergencyStop);
        tryCompare(control("dialogHost"), "visible", true);
        keyClick(Qt.Key_V);
        compare(control("toolpathState").choices.view, "z");
        keyClick(Qt.Key_Escape);
        tryCompare(control("dialogHost"), "visible", false);
        verify(emergencyStop.activeFocus);
        keyClick(Qt.Key_V);
        compare(control("toolpathState").choices.view, "z2");
    }

    function test_submenuHover() {
        const menubar = control("main-menubar");
        click(menubar.itemAt(0));
        const menu = menubar.menuAt(0);
        tryCompare(menu, "opened", true);
        waitForRendering(menu.contentItem);
        const recent = menu.itemAt(1);
        mouseMove(recent, recent.width / 2, recent.height / 2);
        tryCompare(recent, "hovered", true);
        tryCompare(recent.subMenu, "visible", true);
    }

    function test_minimumToolbarKeyboardVisibility() {
        window.width = 760;
        window.height = 640;
        waitForRendering(window.contentItem);
        const viewport = control("toolbar-viewport");
        const last = control("toolbar-view.clear");
        last.forceActiveFocus(Qt.TabFocusReason);
        tryVerify(() => {
            const left = last.mapToItem(viewport, 0, 0).x;
            return left >= -0.5 && left + last.width <= viewport.width + 0.5;
        });
        verify(viewport.contentX > 0);
        const first = control("toolbar-machine.estop");
        first.forceActiveFocus(Qt.BacktabFocusReason);
        tryVerify(() => {
            const left = first.mapToItem(viewport, 0, 0).x;
            return left >= -0.5 && left + first.width <= viewport.width + 0.5;
        });
        compare(viewport.contentX, 0);
    }

    function test_dialogFieldsAndImmediateClose() {
        click(control("workTouchOff"));
        const dialog = control("dialogHost");
        tryCompare(dialog, "visible", true);
        const value = control("touch-value");
        value.forceActiveFocus();
        value.selectAll();
        keyClick(Qt.Key_1);
        keyClick(Qt.Key_2);
        keyClick(Qt.Key_Period);
        keyClick(Qt.Key_5);
        compare(value.text, "12.5");
        keyClick(Qt.Key_Escape);
        tryCompare(dialog, "visible", false);
        click(control("mdiTab"));
        compare(control("manualState").controlTab, "mdi");
        waitForRendering(window.contentItem);
        click(control("mdiHistory1"));
        compare(control("mdiCommand").text, "G0 Z10");
        click(control("manualTab"));
        waitForRendering(window.contentItem);
        click(control("workTouchOff"));
        tryCompare(dialog, "visible", true);
        compare(control("touch-value").text, "0.0");
        mouseClick(window.contentItem, 10, 200);
        tryCompare(dialog, "visible", false);
    }
}
