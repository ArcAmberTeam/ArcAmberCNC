#!/usr/bin/env python3
"""Check AXIS's shipped image contract through Pillow and the actual Tk loader."""
import json
from pathlib import Path
import tkinter as tk
import xml.etree.ElementTree as ET

from PIL import Image

images = Path(__file__).resolve().parents[2] / "share/axis/images"
source = images / "toolbar-source"
icons = json.loads((source / "manifest.json").read_text())["icons"]
names = [icon["file"] for icon in icons]
assert len(names) == len(set(names)) == 21, "Missing or duplicate toolbar entries"
assert (source / "LICENSE").stat().st_size > 0
root = tk.Tk()
root.withdraw()
try:
    for icon in icons:
        name = icon["file"]
        assert Path(name).name == name and name.endswith(".gif"), name
        path = images / name
        expected = (icon["width"], icon["height"])
        assert not path.with_suffix(".png").exists(), f"PNG shadows GIF: {name}"
        assert ET.parse(source / Path(name).with_suffix(".svg")).getroot().tag.endswith("svg")
        with Image.open(path) as im:
            assert im.format == "GIF" and im.size == expected, name
            assert im.n_frames == 1 and "transparency" in im.info, name
            assert im.convert("RGBA").getbbox() is not None, f"Empty icon: {name}"
        photo = tk.PhotoImage(master=root, file=str(path))
        assert (photo.width(), photo.height()) == expected, name
        print(f"PASS {name}: {expected[0]}x{expected[1]}, static transparent GIF, Tk loaded")
finally:
    root.destroy()
