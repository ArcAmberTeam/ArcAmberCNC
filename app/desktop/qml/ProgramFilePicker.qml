pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import BetterCnc.Ui 1.0

Popup {
    id: picker
    property var files: null
    property bool saveMode: false
    signal fileChosen(string path)
    parent: Overlay.overlay
    popupType: Popup.Item
    width: Math.min(700, parent ? parent.width - 32 : 700)
    height: Math.min(500, parent ? parent.height - 32 : 500)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    modal: true
    focus: true
    padding: 20
    closePolicy: Popup.CloseOnEscape
    background: UiSurface { radius: 12 }
    onOpened: { fileName.text = ""; if (files) files.refresh(); }
    function choose(path) { if (path) { fileChosen(path); close(); } }
    contentItem: ColumnLayout {
        spacing: 12
        UiText { text: picker.saveMode ? "程序另存为" : "打开加工程序"; font.pixelSize: 20 }
        RowLayout {
            Repeater {
                model: picker.files ? picker.files.locations : []
                delegate: UiButton {
                    required property string modelData
                    required property int index
                    text: index === 0 ? "加工程序" : "CAM 收件"
                    onClicked: picker.files.browse(modelData)
                }
            }
            Item { Layout.fillWidth: true }
            UiButton { text: "上一级"; onClicked: if (picker.files) picker.files.up(); }
        }
        UiText {
            Layout.fillWidth: true
            text: picker.files ? picker.files.directory : "程序目录不可用"
            color: Theme.secondary
            elide: Text.ElideMiddle
        }
        ListView {
            id: listing
            objectName: "programFileList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: picker.files ? picker.files.entries : []
            spacing: 4
            ScrollBar.vertical: UiScrollBar { }
            delegate: UiButton {
                id: entry
                required property var modelData
                width: listing.width
                text: (modelData.directory ? "▸  " : "") + modelData.name
                tooltip: modelData.name
                contentItem: UiText {
                    text: entry.text
                    color: entry.foreground
                    elide: Text.ElideMiddle
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: {
                    if (modelData.directory) picker.files.browse(modelData.path);
                    else if (picker.saveMode) fileName.text = modelData.name;
                    else picker.choose(modelData.path);
                }
            }
        }
        UiText {
            Layout.fillWidth: true
            visible: text.length > 0
            text: picker.files ? picker.files.message : ""
            color: Theme.danger
            wrapMode: Text.Wrap
        }
        UiTextField {
            id: fileName
            objectName: "programSaveName"
            Layout.fillWidth: true
            visible: picker.saveMode
            placeholderText: "程序文件名，例如 part.ngc"
        }
        RowLayout {
            Item { Layout.fillWidth: true }
            UiButton { text: "取消"; onClicked: picker.close(); }
            UiButton {
                text: "保存"
                visible: picker.saveMode
                enabled: !!picker.files && fileName.text.length > 0
                onClicked: picker.choose(picker.files.destination(fileName.text))
            }
        }
    }
}
