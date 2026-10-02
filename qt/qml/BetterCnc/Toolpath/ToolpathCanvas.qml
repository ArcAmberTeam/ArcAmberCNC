import QtQuick
import BetterCnc.Ui 1.0

// Private native rendering of the Vue preview's static illustration. These paths
// are presentation data, not interpreted machining geometry or live positions.
Canvas {
    id: root
    required property ToolpathState presentation
    objectName: "toolpathCanvas"
    Accessible.role: Accessible.Graphic
    Accessible.name: "LinuxCNC 标识刀路示意图，仅作展示，未经程序解释器计算"
    renderTarget: Canvas.Image

    // Canvas validates a concrete font family rather than accepting the SVG's
    // CSS fallback list. Liberation Sans is the local Debian Arial substitute.
    readonly property string titleFontFamily: {
        const available = Qt.fontFamilies();
        const preferred = ["Arial", "Helvetica", "Liberation Sans", Theme.fontFamily];
        for (let i = 0; i < preferred.length; ++i) {
            if (available.indexOf(preferred[i]) >= 0)
                return preferred[i];
        }
        return Theme.fontFamily;
    }

    readonly property var projections: ({
        "p": [0.94, 0.30, -0.52, 0.78, 144, 216],
        "z": [1, 0, 0, 1, 105, 190],
        "z2": [0.86, -0.32, 0.32, 0.86, 105, 270],
        "x": [0.5, 0, 0, 1, 215, 190],
        "y": [1, 0, 0, 0.3, 105, 245]
    })

    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onVisibleChanged: if (visible) requestPaint()
    Connections {
        target: root.presentation
        function onChoicesChanged() { root.requestPaint(); }
        function onFlagsChanged() { root.requestPaint(); }
        function onZoomChanged() { root.requestPaint(); }
    }

    function polyline(ctx, points, color, lineWidth, dash, fill) {
        ctx.beginPath();
        ctx.moveTo(points[0][0], points[0][1]);
        for (let i = 1; i < points.length; ++i)
            ctx.lineTo(points[i][0], points[i][1]);
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.setLineDash(dash || []);
        if (fill) {
            ctx.closePath();
            ctx.fillStyle = color;
            ctx.fill();
        }
        ctx.stroke();
    }

    onPaint: {
        if (width <= 0 || height <= 0)
            return;
        const ctx = getContext("2d");
        ctx.reset();
        // CSS radial-gradient(ellipse at 50% 40%, #212229, #17181b 70%).
        ctx.save();
        ctx.scale(width, height);
        const backdrop = ctx.createRadialGradient(0.5, 0.4, 0, 0.5, 0.4, 0.72);
        backdrop.addColorStop(0, "#212229");
        backdrop.addColorStop(0.7, "#17181b");
        ctx.fillStyle = backdrop;
        ctx.fillRect(0, 0, 1, 1);
        ctx.restore();

        // SVG's default xMidYMid meet mapping is retained on window resizing.
        const fit = Math.min(width / 740, height / 520);
        ctx.translate((width - 740 * fit) / 2, (height - 520 * fit) / 2);
        ctx.scale(fit, fit);
        ctx.lineJoin = "round";
        ctx.save();
        ctx.translate(370, 260);
        ctx.scale(presentation.zoom, presentation.zoom);
        ctx.translate(-370, -260);
        ctx.save();
        const projection = projections[presentation.choices.view] || projections.p;
        const scale = fit * presentation.zoom;
        // Set the fully composed affine matrix explicitly: QML Canvas's
        // transform multiplication order differs from the SVG group sequence.
        ctx.setTransform(scale * projection[0], scale * projection[1],
                         scale * projection[2], scale * projection[3],
                         (width - 740 * fit) / 2 + fit * (370 + presentation.zoom * (projection[4] - 370)),
                         (height - 520 * fit) / 2 + fit * (260 + presentation.zoom * (projection[5] - 260)));

        if (presentation.choices.grid !== "off") {
            ctx.save();
            ctx.beginPath();
            ctx.rect(-50, -50, 630, 200);
            ctx.clip();
            for (let gx = -72; gx <= 600; gx += 24)
                polyline(ctx, [[gx, -50], [gx, 150]], "#244242", 0.6);
            for (let gy = -72; gy <= 168; gy += 24)
                polyline(ctx, [[-50, gy], [580, gy]], "#244242", 0.6);
            ctx.restore();
        }
        if (presentation.flags["show.limits"]) {
            polyline(ctx, [[-70,-80],[610,-80],[610,190],[-70,190],[-70,-80]], "#6b7278", 1, [5,5]);
            polyline(ctx, [[-70,-80],[-35,-115],[645,-115],[645,155],[610,190]], "#6b7278", 1, [5,5]);
            polyline(ctx, [[610,-80],[645,-115]], "#6b7278", 1, [5,5]);
            polyline(ctx, [[645,155],[-35,155],[-70,190]], "#6b7278", 1, [5,5]);
            polyline(ctx, [[-35,155],[-35,-115]], "#6b7278", 1, [5,5]);
        }
        if (presentation.flags["show.extents"]) {
            polyline(ctx, [[-15,-18],[547,-18],[547,113],[-15,113],[-15,-18]], "#626579", 1);
            const dimensions = [
                [[-15,125],[-15,146]], [[547,125],[547,146]], [[-15,137],[547,137]],
                [[-26,-18],[-44,-18]], [[-26,113],[-44,113]], [[-35,-18],[-35,113]]
            ];
            for (let d = 0; d < dimensions.length; ++d)
                polyline(ctx, dimensions[d], "#626579", 1);
            const arrows = [
                [[-15,137],[-7,134],[-7,140]], [[547,137],[539,134],[539,140]],
                [[-35,-18],[-38,-10],[-32,-10]], [[-35,113],[-38,105],[-32,105]]
            ];
            for (let a = 0; a < arrows.length; ++a)
                polyline(ctx, arrows[a], "#626579", 1, [], true);
            ctx.font = "13px '" + Theme.mono + "'";
            ctx.fillStyle = "#a0a2b5";
            ctx.fillText(presentation.choices.units === "mm" ? "132.000" : "5.1969", 234, 155);
            ctx.save();
            ctx.translate(-57, 73);
            ctx.rotate(-Math.PI / 2);
            ctx.fillText(presentation.choices.units === "mm" ? "31.000" : "1.2205", 0, 0);
            ctx.restore();
        }
        if (presentation.flags["show.program"]) {
            ctx.save();
            ctx.globalAlpha = presentation.flags["show.alpha"] ? 0.55 : 1;
            ctx.font = "italic bold 97px '" + titleFontFamily + "'";
            ctx.save();
            ctx.scale(528 / ctx.measureText("LinuxCNC").width, 1);
            ctx.strokeStyle = "#b2b9e8";
            ctx.lineWidth = 0.9;
            ctx.setLineDash([]);
            ctx.strokeText("LinuxCNC", 0, 84);
            ctx.restore();
            if (presentation.flags["show.rapids"])
                polyline(ctx, [[0,85],[52,2],[61,85],[104,2],[112,85],[170,16],[183,85],[250,15],[265,85],[334,0],[349,85],[419,0],[429,85],[520,4]], "#7977b7", 0.8, [4,4]);
            ctx.restore();
        }
        if (presentation.flags["show.live"])
            polyline(ctx, [[-2,92],[38,92],[46,65]], "#a74949", 1.2);
        if (presentation.flags["show.offsets"]) {
            polyline(ctx, [[0,0],[65,0]], "#7c76dd", 1);
            polyline(ctx, [[0,0],[0,-60]], "#7c76dd", 1);
            ctx.fillStyle = "#aaa6ef";
            ctx.font = "15px '" + Theme.fontFamily + "'";
            ctx.fillText("G54", 5, -66);
        }
        ctx.restore();

        if (presentation.flags["show.tool"]) {
            ctx.save();
            ctx.translate(150, 185);
            ctx.beginPath();
            ctx.moveTo(-18,-36);
            ctx.quadraticCurveTo(0,-45,18,-36);
            ctx.lineTo(7,-7);
            ctx.lineTo(0,8);
            ctx.lineTo(-7,-7);
            ctx.closePath();
            const toolFill = ctx.createLinearGradient(-18, 0, 18, 0);
            toolFill.addColorStop(0, "rgba(221,221,221,0.65)");
            toolFill.addColorStop(1, "rgba(92,107,116,0.45)");
            ctx.fillStyle = toolFill;
            ctx.fill();
            ctx.strokeStyle = "#9aadb5";
            ctx.lineWidth = 0.7;
            ctx.setLineDash([]);
            ctx.stroke();
            ctx.beginPath();
            ctx.ellipse(-18, -41, 36, 10);
            ctx.fillStyle = "rgba(148,160,165,0.4)";
            ctx.fill();
            polyline(ctx, [[0,-51],[0,15]], "#a3aeb3", 0.7, [2,3]);
            ctx.restore();
        }
        ctx.restore();

        ctx.translate(57, 440);
        polyline(ctx, [[0,0],[47,17]], "#de4a49", 1.2);
        polyline(ctx, [[0,0],[-20,27]], "#4aa45a", 1.2);
        polyline(ctx, [[0,0],[0,-51]], "#799dce", 1.2);
        ctx.font = "13px '" + Theme.mono + "'";
        ctx.fillStyle = "#de6b64";
        ctx.fillText("X", 52, 23);
        ctx.fillStyle = "#68b576";
        ctx.fillText("Y", -30, 37);
        ctx.fillStyle = "#799dce";
        ctx.fillText("Z", -4, -59);
    }
}
