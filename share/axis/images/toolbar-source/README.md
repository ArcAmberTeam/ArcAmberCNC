# AXIS toolbar artwork

These SVG sources replace only the existing AXIS toolbar images. Widget commands,
key bindings, layout, selected relief and disabled-state handling are unchanged.
AXIS continues to load static GIFs from the parent directory; no new runtime
dependency is needed. Each GIF keeps the dimensions of the original image.
`tool_axis_y2.png` is replaced by a GIF because AXIS searches for PNG before GIF.

## Source and license

Based on [Lucide](https://github.com/lucide-icons/lucide), revision
`951813ce76a859d4d8b145366972cbb237147a4e`.
The upstream icon name and output dimensions are recorded in `manifest.json`.
Original sources are available at
`https://github.com/lucide-icons/lucide/blob/951813ce76a859d4d8b145366972cbb237147a4e/icons/<source>.svg`.

The complete upstream ISC and Feather MIT notices are preserved in `LICENSE`,
and the shipped GIFs are covered by the corresponding entry in
`debian/copyright`.

Adaptations: dark neutral strokes, blue actions, red emergency/program stops,
gold folder, filled emergency/run/stop shapes, slash for block delete, M1 for
optional pause, and a red slash for resume inhibition. Orthographic view icons
use simplified coordinate frames with X/Y/Z lettering; the rotated Z view keeps
the rotated letter and the inverse Y view uses the opposite corner. Perspective
uses Lucide's box, and mouse rotation uses rotate-3d.

## Regenerate

The generator uses Node.js and the public `sharp` package (tested with 0.35.4).
Install the conversion dependency outside the checkout, then run:

```sh
npm install --prefix /tmp/axis-icon-tools sharp@0.35.4
NODE_PATH=/tmp/axis-icon-tools/node_modules node share/axis/images/toolbar-source/render.cjs
```

Conversion works offline from these SVGs. It rasterizes at 4x density and
downsamples to the original dimensions. GIF has one-bit transparency, so edge
pixels are antialiased against AXIS's existing `#d9d9d9` button face, while empty
pixels stay transparent. A substantially different toolbar background would
require regenerating with a matching matte color.

Only the generated GIFs are needed by the application. The SVGs and renderer are
editable artwork sources, not an alternative UI or a build-time requirement.
