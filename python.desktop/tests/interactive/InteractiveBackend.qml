import QtQml
import ".." as Fixtures

// Only used by tests: commands are recorded; feedback is injected separately.
Fixtures.FakeBackend {
    id: root
    property var initialSnapshot: ({})
    readonly property var document: program
    property int sequence: 0

    Component.onCompleted: {
        initialSnapshot = JSON.parse(JSON.stringify(snapshot));
        reset();
    }
    function dispatch(actionId, payload) {
        sequence++;
        requests = requests.concat([{sequence: sequence, id: actionId, payload: payload}]).slice(-100);
    }
    function openProgram(path) {
        dispatch("file.open", {path: String(path)});
        noticeOccurred("测试模式：仅记录打开请求，不读取文件。使用测试面板加载示例。 ");
        return true;
    }
    function reloadProgram() { dispatch("file.reload", {}); return true; }
    function saveProgram(path, text) {
        dispatch("file.save", {path: String(path), text: text});
        noticeOccurred("测试模式：已记录保存请求，未写入磁盘。");
        return true;
    }
    function saveToolTableText(text) {
        dispatch("tool.save", {text: text});
        noticeOccurred("测试模式：已记录刀具表，未写入磁盘。");
        return true;
    }
    function clearRequests() { requests = []; }
    function reset() {
        snapshot = JSON.parse(JSON.stringify(initialSnapshot));
        sequence = 0;
        clearRequests();
        loadSample();
    }
    function scenario(name) {
        update({connected: name !== "offline", powered: name !== "power-off" && name !== "estop",
            estop: name === "estop", busy: name === "running" || name === "paused",
            paused: name === "paused", mode: name === "running" || name === "paused" ? "auto" : "manual",
            connecting: false, message: "", currentLine: name === "running" || name === "paused" ? 3 : 0});
    }
    function setPosition(axis, value) {
        const point = Array.from(snapshot.actualPosition);
        point[axis] = value;
        update({actualPosition: point, commandedPosition: Array.from(point)});
    }
    function loadSample() {
        document.filePath = "/gui-test/sample.ngc";
        document.fileName = "sample.ngc（测试数据）";
        document.lines = ["G21 G90", "G0 X0 Y0", "G1 X40 Y0 F100", "G1 X40 Y30", "G1 X0 Y30", "G1 X0 Y0", "M2"];
        document.selectedLine = 1;
        document.previewBusy = false;
        document.previewError = "";
        document.bounds = {min: [0, 0, 0], max: [40, 30, 0]};
        document.segments = [
            {type: "feed", start: [0, 0, 0], end: [40, 0, 0], line: 3},
            {type: "feed", start: [40, 0, 0], end: [40, 30, 0], line: 4},
            {type: "feed", start: [40, 30, 0], end: [0, 30, 0], line: 5},
            {type: "feed", start: [0, 30, 0], end: [0, 0, 0], line: 6}
        ];
        update({file: document.filePath, capabilities: {"document.run-line": true}, angularUnits: 1, g5xIndex: 1});
    }
}
