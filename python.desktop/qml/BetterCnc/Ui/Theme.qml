pragma Singleton
import QtQuick

QtObject {
    // Platinum design tokens: presentation only, no machine state.
    readonly property color base: "#F7F6F2"
    readonly property color surface: "#FFFFFF"
    readonly property color sidebar: surface
    readonly property color raised: surface
    readonly property color hover: "#F1F0EC"
    readonly property color input: surface
    readonly property color border: "#E2E2DF"
    readonly property color shadow: "#42464C"
    readonly property color separatorShadow: "#0542464C"
    readonly property color borderControl: "#8D887E"
    readonly property color text: "#24272C"
    readonly property color secondary: "#60656D"
    readonly property color muted: "#7A7D82"
    readonly property color disabled: "#EEECE6"
    readonly property color accent: "#765F32"
    readonly property color accentFill: "#B49A61"
    readonly property color accentHover: "#A98F56"
    readonly property color accentPressed: "#A58B52"
    readonly property color accentSoft: "#F3ECDD"
    readonly property color danger: "#B83F3F"
    readonly property color dangerSoft: "#FBEFED"
    readonly property color success: "#347A52"
    readonly property color successSoft: "#EAF4ED"
    readonly property color warning: "#966A23"
    readonly property color warningSoft: "#FBF3E6"
    readonly property color info: "#386FAA"
    readonly property color rapid: "#5C89B5"
    readonly property color grid: "#E4E3DD"
    readonly property color geometry: "#838A93"
    readonly property color glass: "#FAF9F6" // Solid fallback for the Qt software/Intel renderer.
    readonly property color scrim: "#3D24272C"
    readonly property int gap: 8
    readonly property int padding: 16
    readonly property int radius: 12
    readonly property int controlRadius: 8
    readonly property int controlHeight: 36
    readonly property int bodySize: 14
    readonly property int labelSize: 12
    readonly property int titleSize: 20
    readonly property string fontFamily: {
        const available = Qt.fontFamilies();
        const preferred = ["Inter", "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei"];
        for (let i = 0; i < preferred.length; ++i) {
            if (available.indexOf(preferred[i]) >= 0) return preferred[i];
        }
        return "sans-serif";
    }
    readonly property string mono: {
        const available = Qt.fontFamilies();
        const preferred = ["SFMono-Regular", "Consolas", "Liberation Mono", "Courier New", "Menlo"];
        for (let i = 0; i < preferred.length; ++i) {
            if (available.indexOf(preferred[i]) >= 0) return preferred[i];
        }
        return "monospace";
    }
}
