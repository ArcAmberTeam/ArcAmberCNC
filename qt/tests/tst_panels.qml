pragma ComponentBehavior: Bound

import QtQuick
import QtTest
import BetterCnc.Toolpath 1.0
import BetterCnc.Program 1.0

TestCase {
    id: testCase
    name: "PreviewAndProgramParity"
    when: windowShown
    visible: true
    width: 1100
    height: 820
    property var fixture

    Component {
        id: fixtureComponent
        Item {
            id: panelFixture
            width: testCase.width
            height: testCase.height
            property alias presentation: presentation
            property alias preview: preview
            property alias program: program
            ToolpathState { id: presentation }
            ToolpathPanel {
                id: preview
                x: panelFixture.width <= 900 ? 264 : 296
                y: 146
                width: panelFixture.width - x
                height: panelFixture.height - 337
                compact: panelFixture.width <= 1100
                presentation: panelFixture.presentation
            }
            ProgramPanel {
                id: program
                x: preview.x
                y: panelFixture.height - 184
                width: preview.width
                height: 184
            }
        }
    }
    SignalSpy { id: canvasPainted; signalName: "painted" }
    SignalSpy { id: dialogRequested; signalName: "dialogRequested" }

    function control(name) {
        const item = findChild(fixture, name);
        verify(item !== null, "Missing public UI: " + name);
        return item;
    }
    function init() {
        width = 1100;
        height = 820;
        fixture = createTemporaryObject(fixtureComponent, testCase);
        verify(fixture !== null);
        canvasPainted.target = control("toolpathCanvas");
        dialogRequested.target = fixture.program;
        dialogRequested.clear();
        renderedCanvas();
    }
    function cleanup() {
        canvasPainted.target = null;
        dialogRequested.target = null;
    }
    function renderedCanvas() {
        const canvas = control("toolpathCanvas");
        canvasPainted.clear();
        canvas.requestPaint();
        tryVerify(() => canvasPainted.count > 0, 3000, "Native canvas must finish painting");
        // Capture the root scene so nested clipping and projected coordinates
        // are included consistently by Qt Quick Test's software renderer.
        return grabImage(fixture);
    }
    function test_projectionAndZoomChangeRendering() {
        let previous = renderedCanvas();
        for (const view of ["z", "z2", "x", "y", "p"]) {
            fixture.presentation.setChoice("view", view);
            const current = renderedCanvas();
            verify(!previous.equals(current), "Projection " + view + " must change the drawn geometry");
            previous = current;
        }
        fixture.presentation.zoomBy(1.25);
        verify(!previous.equals(renderedCanvas()), "Zoom must change the drawn geometry");
        compare(control("previewCaption").text, "透视图 · 125%");
        fixture.presentation.zoomBy(100);
        compare(control("previewCaption").text, "透视图 · 200%");
        fixture.presentation.zoomBy(0.001);
        compare(control("previewCaption").text, "透视图 · 50%");
    }
    function test_displayLayersChangeRendering_data() {
        return ["show.program", "show.rapids", "show.alpha", "show.live", "show.tool",
                "show.extents", "show.offsets", "show.limits"].map(flag => ({tag: flag, flag: flag}));
    }
    function test_displayLayersChangeRendering(data) {
        const previous = renderedCanvas();
        fixture.presentation.toggleFlag(data.flag);
        verify(!previous.equals(renderedCanvas()), data.flag + " must change the preview");
    }
    function test_gridChangesRendering() {
        const previous = renderedCanvas();
        fixture.presentation.setChoice("grid", "5");
        verify(!previous.equals(renderedCanvas()), "Enabling the grid must draw grid lines");
    }
    function test_programTitleRendersWithAvailableLocalFont() {
        // Linux's installed Liberation fonts exercise this without Arial.
        // Disable the rapid lines so they cannot hide a missing title glyph.
        failOnWarning(/Context2D: The font families specified are invalid:.*/);
        for (const flag of ["show.program", "show.rapids", "show.live", "show.tool", "show.extents"])
            fixture.presentation.setFlag(flag, false);
        const withoutTitle = renderedCanvas();
        fixture.presentation.setFlag("show.program", true);
        verify(!withoutTitle.equals(renderedCanvas()), "The LinuxCNC outline must render using an installed local font");
    }
    function test_tabsReadoutsAndUnits() {
        fixture.presentation.setChoice("units", "inch");
        compare(control("coordinateX").text, "0.0000");
        fixture.presentation.setFlag("show.velocity", false);
        compare(control("velocityReadout").visible, false);
        fixture.presentation.setFlag("show.offsets", true);
        compare(control("offsetReadout").visible, true);
        mouseClick(control("droTab"));
        compare(control("droPanel").visible, true);
        compare(control("toolpathCanvas").visible, false);
        compare(control("droCoordinateX").text, "0.0000");
        fixture.presentation.setFlag("show.large", true);
        compare(control("droCoordinateX").font.pixelSize, 46);
        fixture.presentation.setChoice("units", "mm");
        compare(control("droCoordinateX").text, "0.000");
        keyClick(Qt.Key_Left);
        compare(control("toolpathCanvas").visible, true);
        compare(control("droPanel").visible, false);
    }
    function test_programSelectionAndContextAction() {
        mouseClick(fixture.program, 200, 70);
        compare(control("programLine1").Accessible.selected, true);
        keyClick(Qt.Key_Down);
        compare(control("programLine2").Accessible.selected, true);
        compare(control("programLine1").Accessible.selected, false);
        keyClick(Qt.Key_Up);
        compare(control("programLine1").Accessible.selected, true);
        mouseClick(fixture.program, 200, 70, Qt.RightButton);
        tryCompare(control("programContextMenu"), "visible", true);
        mouseClick(control("runFromLineAction"));
        tryCompare(dialogRequested, "count", 1);
        compare(dialogRequested.signalArguments[0][0], "program.run-line");
        compare(dialogRequested.signalArguments[0][1], "从此行运行");
    }
    function test_smallWindowKeepsPreviewVisible() {
        width = 760;
        height = 640;
        tryCompare(fixture.preview, "width", 496);
        const image = renderedCanvas();
        compare(image.width, 760);
        compare(image.height, 640);
        verify(control("toolpathCanvas").height > 100);
        compare(control("coordinateZ").visible, true);
        image.save("preview-minimum.png");
    }
    function test_smallWindowReadoutsWrapWithoutClipping() {
        width = 760;
        height = 640;
        fixture.presentation.setFlag("show.large", true);
        fixture.presentation.setFlag("show.dtg", true);
        fixture.presentation.setFlag("show.offsets", true);
        fixture.presentation.setChoice("units", "inch");
        renderedCanvas();
        for (const axis of ["X", "Y", "Z"]) {
            for (const prefix of ["coordinate", "distanceToGo"]) {
                const reading = control(prefix + axis);
                verify(reading.visible);
                const position = reading.mapToItem(fixture.preview, 0, 0);
                verify(position.x >= 0 && position.x + reading.width <= fixture.preview.width,
                       prefix + axis + " must fit without horizontal clipping");
                verify(position.y >= 44 && position.y + reading.height <= fixture.preview.height,
                       prefix + axis + " must fit below the tabs");
            }
        }
    }
}
