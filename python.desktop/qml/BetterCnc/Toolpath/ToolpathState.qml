import QtQuick

QtObject {
    id: root
    objectName: "toolpathState"

    property string previewTab: "preview"
    property real zoom: 1
    property bool rotate: false
    property real yaw: 0
    property real pitch: 0
    property real panX: 0
    property real panY: 0
    readonly property real minimumZoom: 0.1
    readonly property real maximumZoom: 20
    property int liveResetRevision: 0

    function clearLive(): void {
        liveResetRevision++;
    }
    property var choices: ({
        "view": "p", "units": "mm", "grid": "off",
        "position": "actual", "coordinates": "relative"
    })
    property var flags: ({
        "show.program": true, "show.rapids": true, "show.alpha": false,
        "show.live": true, "show.tool": true, "show.extents": true,
        "show.offsets": false, "show.limits": false, "show.velocity": true,
        "show.dtg": false, "show.large": false
    })

    function zoomBy(factor: real): void {
        if (!isFinite(factor) || factor <= 0) return;
        zoom = Math.max(minimumZoom, Math.min(maximumZoom, zoom * factor));
    }

    function resetView(): void {
        zoom = 1; panX = 0; panY = 0; yaw = 0; pitch = 0;
    }

    function panBy(dx: real, dy: real): void {
        if (!isFinite(dx) || !isFinite(dy)) return;
        panX += dx; panY += dy;
    }

    function orbitBy(dx: real, dy: real): void {
        if (!isFinite(dx) || !isFinite(dy)) return;
        // Leave the planar preset before orbiting around the program center.
        if (choices.view !== "p") setChoice("view", "p");
        yaw = (yaw + dx / 150) % (2 * Math.PI);
        pitch = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, pitch + dy / 150));
    }

    function setChoice(group: string, value: string): void {
        const updated = Object.assign({}, choices);
        updated[group] = value;
        choices = updated;
        if (group === "view") resetView();
    }

    function toggleFlag(flagId: string): void {
        setFlag(flagId, !flags[flagId]);
    }

    function setFlag(flagId: string, enabled: bool): void {
        const updated = Object.assign({}, flags);
        updated[flagId] = enabled;
        flags = updated;
    }
}
