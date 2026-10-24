pragma ComponentBehavior: Bound
import QtQuick
import BetterCnc.Ui 1.0

Flickable {
    id: root
    required property ToolpathState presentation
    contentWidth: controls.width
    contentHeight: height
    boundsBehavior: Flickable.StopAtBounds
    flickableDirection: Flickable.HorizontalFlick
    clip: true
    Row {
        id: controls
        spacing: 4
        Repeater {
            model: [
                {id: "pan", text: "平移", tip: "单指 / 左键拖动平移"},
                {id: "orbit", text: "旋转", tip: "单指 / 左键拖动旋转；右键始终旋转"},
                {id: "zoom-out", text: "−", tip: "缩小；双指捏合缩放"},
                {id: "zoom-in", text: "+", tip: "放大；滚轮围绕指针缩放"},
                {id: "fit", text: "复位", tip: "复位并适配视图；也可双击 / 双击触屏"},
                {id: "top", text: "俯视", tip: "切换到 XY 俯视图"}
            ]
            UiButton {
                id: button
                required property var modelData
                objectName: "viewport-" + modelData.id
                width: modelData.id.startsWith("zoom") ? 44 : 56
                height: 44
                kind: "tab"
                text: modelData.text
                tooltip: modelData.tip
                selected: modelData.id === "pan" && !root.presentation.rotate
                       || modelData.id === "orbit" && root.presentation.rotate
                onClicked: {
                    switch (modelData.id) {
                    case "pan": root.presentation.rotate = false; break;
                    case "orbit": root.presentation.rotate = true; break;
                    case "zoom-out": root.presentation.zoomBy(1 / 1.25); break;
                    case "zoom-in": root.presentation.zoomBy(1.25); break;
                    case "fit": root.presentation.resetView(); break;
                    case "top": root.presentation.setChoice("view", "z"); break;
                    }
                }
                onActiveFocusChanged: {
                    if (!activeFocus) return;
                    root.contentX = Math.max(0, Math.min(root.contentWidth - root.width,
                        x < root.contentX ? x : x + width > root.contentX + root.width ? x + width - root.width : root.contentX));
                }
            }
        }
    }
}
