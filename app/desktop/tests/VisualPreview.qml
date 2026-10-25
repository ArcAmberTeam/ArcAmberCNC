pragma ComponentBehavior: Bound
import QtQuick
import "../qml" as App

// Explicit visual fixture. Never loaded by the production launcher.
App.Main {
    id: root
    property string scenario: "ready"
    title: "视觉验收 · 测试数据 — BetterLinuxCNC"
    backend: FakeBackend {
        readonly property var document: program
        Component.onCompleted: {
            document.segments = [
                {type: "rapid", start: [0, 0, 10], end: [0, 0, 0], line: 2},
                {type: "feed", start: [0, 0, 0], end: [40, 0, 0], line: 3},
                {type: "feed", start: [40, 0, 0], end: [40, 30, 0], line: 4},
                {type: "feed", start: [40, 30, 0], end: [0, 30, 0], line: 5},
                {type: "feed", start: [0, 30, 0], end: [0, 0, 0], line: 6}
            ];
            document.bounds = {min: [0, 0, 0], max: [40, 30, 10]};
            document.lines = ["(GUI visual fixture)", "G0 X0 Y0 Z10", "G1 Z0 F100", "G1 X40", "G1 Y30", "G1 X0", "G1 Y0", "M2"];
            if (root.scenario === "offline") update({connected: false, axes: [], message: ""});
            if (root.scenario === "error") Qt.callLater(() => errorOccurred("测试错误：控制器拒绝了操作，请检查设备状态。"));
        }
    }
}
