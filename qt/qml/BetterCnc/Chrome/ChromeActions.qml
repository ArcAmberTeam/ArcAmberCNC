import QtQuick
import BetterCnc.Catalog 1.0
import BetterCnc.Manual 1.0
import BetterCnc.Toolpath 1.0

// Entry composition owns only local presentation changes and dialog requests.
QtObject {
    id: root
    required property ManualState manual
    required property ToolpathState preview
    signal dialogRequested(string actionId, string title, string axis)

    function selectedValue(group) {
        if (group === "mode") return manual.mode;
        if (group === "touch") return manual.touchTarget;
        return preview.choices[group] || "";
    }

    function isSelected(item) {
        return item.kind === "radio"
            ? selectedValue(item.group) === item.value
            : !!preview.flags[item.id];
    }

    function activate(id, label) {
        if (id === "view.zoom-in") { preview.zoomBy(1.15); return; }
        if (id === "view.zoom-out") { preview.zoomBy(1 / 1.15); return; }
        if (id === "view.rotate") { preview.rotate = !preview.rotate; return; }
        if (id === "view.clear") { preview.setFlag("show.live", false); return; }
        const item = Catalog.findItem(id);
        if (item && item.kind === "radio") {
            if (item.group === "mode") manual.mode = item.value;
            else if (item.group === "touch") manual.touchTarget = item.value;
            else preview.setChoice(item.group, item.value);
            return;
        }
        if (item && item.kind === "check" && id in preview.flags) {
            preview.toggleFlag(id);
            return;
        }
        const title = item ? item.label.replace("…", "") : (label || "操作说明");
        dialogRequested(id, title, manual.selectedAxis);
    }
}
