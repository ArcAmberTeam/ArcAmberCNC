import QtQuick
import BetterCnc.Ui 1.0
import "Coordinates.js" as Coordinates

// Geometry is received once per interpreted program. Status updates redraw only
// the lightweight overlay; they never copy/rebuild the full segment collection.
Canvas {
    id: root
    required property ToolpathState presentation
    property var machine: null
    property var program: null
    objectName: "toolpathCanvas"
    Accessible.role: Accessible.Graphic
    Accessible.name: "RS274 程序刀路预览；不是材料去除仿真"
    renderTarget: Canvas.Image
    property var geometry: []
    property var geometryBounds: ({min: [-25, -25, -25], max: [25, 25, 25]})
    readonly property var pivot: geometryBounds.min.map((v, i) => (v + geometryBounds.max[i]) / 2)
    property var segmentsByLine: ({})
    property var livePoints: []
    readonly property real yaw: presentation.yaw
    readonly property real pitch: presentation.pitch
    clip: true
    activeFocusOnTab: true
    readonly property var viewport: frame()

    function syncProgram() {
        geometry = program && program.segments ? program.segments : [];
        syncBounds();
        const byLine = {};
        for (let i = 0; i < geometry.length; ++i) {
            const segment = geometry[i];
            if (!byLine[segment.line]) byLine[segment.line] = [];
            byLine[segment.line].push(segment);
        }
        segmentsByLine = byLine;
        requestPaint();
        overlay.requestPaint();
    }
    function syncBounds() {
        const bounds = program ? program.bounds : null;
        geometryBounds = bounds && bounds.min && bounds.min.length === 3 && bounds.max && bounds.max.length === 3
                ? bounds : ({min: [-25, -25, -25], max: [25, 25, 25]});
    }
    function observePosition() {
        const point = Coordinates.tip(machine);
        if (point) {
            const previous = livePoints.length ? livePoints[livePoints.length - 1] : null;
            if (!previous || point.some((value, i) => Math.abs(value - previous[i]) > 0.001)) {
                livePoints.push(point);
                if (livePoints.length > 5000) livePoints.shift();
            }
        } else if (livePoints.length) {
            // A reconnect must not draw a fictitious connecting movement.
            livePoints = [];
        }
        overlay.requestPaint();
    }
    function projected(point, unrotated = false) {
        const center = pivot;
        let x = point[0] - center[0], y = point[1] - center[1], z = point[2] - center[2];
        if (!unrotated && (yaw || pitch)) {
            const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
            const rx = x * cy - y * sy, ry = x * sy + y * cy;
            x = rx; y = ry * cp - z * sp; z = ry * sp + z * cp;
        }
        switch (presentation.choices.view) {
        case "z": return [x, -y];
        case "z2": return [0.86 * x + 0.32 * y, 0.32 * x - 0.86 * y];
        case "x": return [y, -z];
        case "y": return [x, -z];
        default: return [0.94 * x - 0.52 * y, 0.30 * x + 0.78 * y - 0.9 * z];
        }
    }
    function frame() {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (let i = 0; i < 8; ++i) {
            const point = projected([geometryBounds[(i & 1) ? "max" : "min"][0],
                                     geometryBounds[(i & 2) ? "max" : "min"][1],
                                     geometryBounds[(i & 4) ? "max" : "min"][2]], true);
            minX = Math.min(minX, point[0]); maxX = Math.max(maxX, point[0]);
            minY = Math.min(minY, point[1]); maxY = Math.max(maxY, point[1]);
        }
        const padding = Math.min(45, height * 0.15, width * 0.1);
        const scale = Math.max(0.01, Math.min(Math.max(1, width - padding * 2) / Math.max(1, maxX - minX),
                                            Math.max(1, height - padding * 2) / Math.max(1, maxY - minY))) * presentation.zoom;
        return {scale: scale, x: width / 2 + presentation.panX,
                y: height / 2 + presentation.panY};
    }
    function screen(point) {
        const p = projected(point);
        return [p[0] * viewport.scale + viewport.x, p[1] * viewport.scale + viewport.y];
    }
    function line(ctx, start, end) {
        const a = screen(start), b = screen(end);
        ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]);
    }
    function box(ctx, low, high) {
        const corners = [];
        for (let i = 0; i < 8; ++i)
            corners.push([(i & 1) ? high[0] : low[0], (i & 2) ? high[1] : low[1], (i & 4) ? high[2] : low[2]]);
        ctx.beginPath();
        for (let vertex = 0; vertex < 8; ++vertex)
            for (let bit = 1; bit <= 4; bit *= 2)
                if (!(vertex & bit)) line(ctx, corners[vertex], corners[vertex | bit]);
        ctx.stroke();
    }
    onProgramChanged: syncProgram()
    onMachineChanged: observePosition()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onViewportChanged: { requestPaint(); overlay.requestPaint(); }
    onVisibleChanged: if (visible) { requestPaint(); overlay.requestPaint(); }
    Component.onCompleted: { syncProgram(); observePosition(); }
    Connections {
        target: root.program
        ignoreUnknownSignals: true
        function onSegmentsChanged() { root.syncProgram(); }
        function onBoundsChanged() { root.syncBounds(); }
        // The Python document shares one notify signal for its geometry fields.
        function onChanged() { root.syncProgram(); }
        function onSelectedLineChanged() { overlay.requestPaint(); }
    }
    Connections {
        target: root.presentation
        function onChoicesChanged() { root.requestPaint(); overlay.requestPaint(); }
        function onFlagsChanged() { root.requestPaint(); overlay.requestPaint(); }
        function onYawChanged() { root.requestPaint(); overlay.requestPaint(); }
        function onPitchChanged() { root.requestPaint(); overlay.requestPaint(); }
        function onLiveResetRevisionChanged() { root.livePoints = []; overlay.requestPaint(); }
    }
    onPaint: {
        if (width <= 0 || height <= 0) return;
        const ctx = getContext("2d");
        ctx.reset();
        const backdrop = ctx.createRadialGradient(width / 2, height * 0.4, 0,
                                                  width / 2, height * 0.4, Math.max(width, height) * 0.7);
        backdrop.addColorStop(0, Theme.base); backdrop.addColorStop(1, Theme.glass);
        ctx.fillStyle = backdrop; ctx.fillRect(0, 0, width, height);
        if (presentation.choices.grid !== "off") {
            let spacing = parseFloat(presentation.choices.grid);
            if (String(presentation.choices.grid).indexOf("in") >= 0) spacing *= 25.4;
            if (spacing > 0) {
                const low = geometryBounds.min, high = geometryBounds.max;
                // A user-defined tiny grid must not freeze the UI.
                const count = Math.max((high[0] - low[0]) / spacing, (high[1] - low[1]) / spacing);
                if (count > 200) spacing *= Math.ceil(count / 200);
                ctx.strokeStyle = Theme.grid; ctx.lineWidth = 0.7; ctx.beginPath();
                for (let x = Math.floor(low[0] / spacing) * spacing; x <= high[0] + spacing; x += spacing)
                    line(ctx, [x, low[1], 0], [x, high[1], 0]);
                for (let y = Math.floor(low[1] / spacing) * spacing; y <= high[1] + spacing; y += spacing)
                    line(ctx, [low[0], y, 0], [high[0], y, 0]);
                ctx.stroke();
            }
        }
        if (geometry.length && presentation.flags["show.program"]) {
            ctx.globalAlpha = presentation.flags["show.alpha"] ? 0.55 : 1;
            for (const kind of ["rapid", "feed"]) {
                if (kind === "rapid" && !presentation.flags["show.rapids"]) continue;
                ctx.strokeStyle = kind === "rapid" ? Theme.rapid : Theme.accentFill;
                ctx.lineWidth = kind === "rapid" ? 1 : 1.5;
                ctx.setLineDash(kind === "rapid" ? [4, 4] : []);
                ctx.beginPath();
                for (let i = 0; i < geometry.length; ++i)
                    if (geometry[i].type === kind) line(ctx, geometry[i].start, geometry[i].end);
                ctx.stroke();
            }
            ctx.globalAlpha = 1;
        }
        ctx.setLineDash([]);
        if (geometry.length && presentation.flags["show.extents"]) {
            ctx.strokeStyle = Theme.geometry; ctx.lineWidth = 0.7;
            box(ctx, geometryBounds.min, geometryBounds.max);
            ctx.fillStyle = Theme.secondary; ctx.font = "11px '" + Theme.mono + "'";
            const divisor = presentation.choices.units === "inch" ? 25.4 : 1;
            const dimensions = geometryBounds.max.map((v, i) => ((v - geometryBounds.min[i]) / divisor).toFixed(3));
            ctx.fillText(dimensions.join(" × ") + (divisor === 1 ? " mm" : " in"), 20, height - 15);
        }
        // Coordinate axes remain a frame reference when no program is loaded.
        ctx.lineWidth = 1.2;
        const origin = [38, height - 38];
        const center = pivot;
        const projectedCenter = projected(center);
        for (const axis of [{index: 0, color: Theme.danger, label: "X"},
                            {index: 1, color: Theme.success, label: "Y"},
                            {index: 2, color: Theme.info, label: "Z"}]) {
            const endpoint = center.slice(); endpoint[axis.index] += 1;
            const direction = projected(endpoint);
            const to = [(direction[0] - projectedCenter[0]) * 30, (direction[1] - projectedCenter[1]) * 30];
            ctx.strokeStyle = axis.color; ctx.fillStyle = axis.color;
            ctx.beginPath(); ctx.moveTo(origin[0], origin[1]);
            ctx.lineTo(origin[0] + to[0], origin[1] + to[1]); ctx.stroke();
            ctx.font = "11px '" + Theme.mono + "'";
            ctx.fillText(axis.label, origin[0] + to[0] + 3, origin[1] + to[1] - 3);
        }
    }
    Canvas {
        id: overlay
        objectName: "toolpathLiveOverlay"
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx = getContext("2d"); ctx.reset();
            if (!root.machine || !root.machine.connected) return;
            if (root.presentation.flags["show.limits"] && root.machine.axisLimits && root.machine.linearUnits > 0) {
                const limits = root.machine.axisLimits;
                if (["X", "Y", "Z"].every(a => limits[a] && limits[a].min !== null && limits[a].max !== null)) {
                    ctx.strokeStyle = Theme.geometry; ctx.lineWidth = 1; ctx.setLineDash([5, 5]);
                    root.box(ctx, ["X", "Y", "Z"].map(a => limits[a].min / root.machine.linearUnits),
                             ["X", "Y", "Z"].map(a => limits[a].max / root.machine.linearUnits));
                    ctx.setLineDash([]);
                }
            }
            if (root.presentation.flags["show.live"] && root.livePoints.length > 1) {
                ctx.strokeStyle = Theme.danger; ctx.lineWidth = 1.2; ctx.beginPath();
                for (let i = 1; i < root.livePoints.length; ++i) root.line(ctx, root.livePoints[i - 1], root.livePoints[i]);
                ctx.stroke();
            }
            for (const selection of [{line: root.machine.currentLine, color: Theme.success},
                                     {line: root.program ? root.program.selectedLine : 0, color: Theme.accent}]) {
                const segments = root.segmentsByLine[selection.line] || [];
                ctx.strokeStyle = selection.color; ctx.lineWidth = 2; ctx.beginPath();
                for (let j = 0; j < segments.length; ++j) root.line(ctx, segments[j].start, segments[j].end);
                ctx.stroke();
            }
            if (root.presentation.flags["show.offsets"]) {
                const work = Coordinates.vector(root.machine, "g5xOffset");
                if (work && root.machine.linearUnits > 0) {
                    const p = root.screen(work.slice(0, 3).map(v => v / root.machine.linearUnits));
                    ctx.strokeStyle = Theme.accent; ctx.lineWidth = 1;
                    ctx.beginPath(); ctx.moveTo(p[0] - 9, p[1]); ctx.lineTo(p[0] + 9, p[1]);
                    ctx.moveTo(p[0], p[1] - 9); ctx.lineTo(p[0], p[1] + 9); ctx.stroke();
                    ctx.font = "11px '" + Theme.fontFamily + "'"; ctx.fillStyle = Theme.accent;
                    ctx.fillText(Coordinates.workLabel(root.machine), p[0] + 6, p[1] - 12);
                }
            }
            const tip = Coordinates.tip(root.machine);
            if (tip && root.presentation.flags["show.tool"]) {
                const p = root.screen(tip);
                ctx.beginPath(); ctx.moveTo(p[0] - 7, p[1] - 24); ctx.lineTo(p[0] + 7, p[1] - 24);
                ctx.lineTo(p[0], p[1]); ctx.closePath();
                ctx.fillStyle = Theme.accentFill; ctx.fill();
                ctx.strokeStyle = Theme.geometry; ctx.lineWidth = 0.8; ctx.stroke();
            }
        }
    }
    function zoomAt(factor, x, y) {
        const before = presentation.zoom;
        presentation.zoomBy(factor);
        const ratio = presentation.zoom / before;
        presentation.panX = (x - width / 2) - (x - width / 2 - presentation.panX) * ratio;
        presentation.panY = (y - height / 2) - (y - height / 2 - presentation.panY) * ratio;
    }
    ViewportGestures {
        anchors.fill: parent
        rotate: root.presentation.rotate
        enabled: root.visible && (!root.Window.window || root.Window.window.active)
        onInteractionStarted: root.forceActiveFocus(Qt.MouseFocusReason)
        onPanRequested: (dx, dy) => root.presentation.panBy(dx, dy)
        onOrbitRequested: (dx, dy) => root.presentation.orbitBy(dx, dy)
        onZoomRequested: (factor, x, y) => root.zoomAt(factor, x, y)
        onResetRequested: root.presentation.resetView()
    }
    // Camera focus must not bubble arrow/Page keys into machine jogging.
    Keys.onShortcutOverride: event => {
        if ([Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
             Qt.Key_PageUp, Qt.Key_PageDown, Qt.Key_Home, Qt.Key_End].indexOf(event.key) >= 0)
            event.accepted = true;
    }
    Keys.onPressed: event => {
        switch (event.key) {
        case Qt.Key_Left: presentation.panBy(-20, 0); break;
        case Qt.Key_Right: presentation.panBy(20, 0); break;
        case Qt.Key_Up: presentation.panBy(0, -20); break;
        case Qt.Key_Down: presentation.panBy(0, 20); break;
        case Qt.Key_PageUp: presentation.zoomBy(1.25); break;
        case Qt.Key_PageDown: presentation.zoomBy(1 / 1.25); break;
        case Qt.Key_Home: presentation.resetView(); break;
        case Qt.Key_End: break;
        default: return;
        }
        event.accepted = true;
    }
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.width: 2
        border.color: Theme.accent
        visible: root.activeFocus
    }
}
