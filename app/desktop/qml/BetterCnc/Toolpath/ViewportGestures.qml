import QtQuick

// Pointer ownership stays inside the view; these signals never submit commands.
Item {
    id: root
    property bool rotate: false
    signal panRequested(real dx, real dy)
    signal orbitRequested(real dx, real dy)
    signal zoomRequested(real factor, real x, real y)
    signal resetRequested()
    signal interactionStarted()

    HoverHandler { cursorShape: singleDrag.active || alternateDrag.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor }
    DragHandler {
        id: singleDrag
        target: null
        acceptedButtons: Qt.LeftButton
        maximumPointCount: 1
        enabled: !pinch.active
        onActiveChanged: if (active) root.interactionStarted()
        onTranslationChanged: delta => {
            if (!active) return;
            if (root.rotate) root.orbitRequested(delta.x, delta.y);
            else root.panRequested(delta.x, delta.y);
        }
    }
    DragHandler {
        id: alternateDrag
        target: null
        acceptedDevices: PointerDevice.Mouse | PointerDevice.Stylus
        acceptedButtons: Qt.MiddleButton | Qt.RightButton
        onActiveChanged: if (active) root.interactionStarted()
        onTranslationChanged: delta => {
            if (!active) return;
            if (centroid.pressedButtons & Qt.RightButton) root.orbitRequested(delta.x, delta.y);
            else root.panRequested(delta.x, delta.y);
        }
    }
    PinchHandler {
        id: pinch
        target: null
        minimumPointCount: 2
        maximumPointCount: 2
        rotationAxis.enabled: false
        onActiveChanged: if (active) root.interactionStarted()
        onScaleChanged: delta => { if (active) root.zoomRequested(delta, centroid.position.x, centroid.position.y); }
        onTranslationChanged: delta => { if (active) root.panRequested(delta.x, delta.y); }
    }
    WheelHandler {
        target: null
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: event => {
            root.interactionStarted();
            if ((event.pixelDelta.x || event.pixelDelta.y) && !(event.modifiers & Qt.ControlModifier)) {
                root.panRequested(event.pixelDelta.x, event.pixelDelta.y);
            } else {
                const delta = event.pixelDelta.y || event.angleDelta.y;
                if (delta) root.zoomRequested(Math.exp(delta / 600), event.x, event.y);
            }
            event.accepted = true;
        }
    }
    TapHandler {
        acceptedButtons: Qt.LeftButton
        onTapped: root.interactionStarted()
        onDoubleTapped: { root.interactionStarted(); root.resetRequested(); }
    }
}
