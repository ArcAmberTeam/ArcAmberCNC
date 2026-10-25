"""Generate a separate commissioning profile after inputs and travel are verified."""
import argparse
import json
import math
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "mesa/board/zhulong-v2.json"


def prepare(settings: dict, destination: Path, *, board_path: Path = BOARD_PATH) -> Path:
    """Read the public board/settings files; never overwrite an existing profile."""
    board = json.loads(board_path.read_text())
    distance = board["homing"]["distance_mm"]
    if type(distance) not in (int, float) or not math.isfinite(distance) or distance <= 0:
        raise ValueError("Retreat distance must be a finite positive distance in mm")
    active_low = board["homing"]["active_low"]
    if type(active_low) is not bool:
        raise ValueError("homing.active_low must be a boolean")
    # These joint directions and inputs are the contract of zhulong_homing.
    for axis, gpio, direction in (("X", 20, -1), ("Y", 21, 1), ("Z", 22, -1)):
        mapping = board["homing"]["axes"].get(axis, {})
        if type(mapping.get("gpio")) is not int or type(mapping.get("direction")) is not int or mapping != {"gpio": gpio, "direction": direction}:
            raise ValueError(f"{axis}: zhulong_homing requires GPIO {gpio}, direction {direction}")
    if settings.get("switch_inputs_verified") is not True:
        raise ValueError("Verify all XYZ inputs: untouched inactive, touched active, released inactive; then set switch_inputs_verified=true")
    lengths = settings.get("usable_travel_from_switch_mm", {})
    if not isinstance(lengths, dict):
        raise ValueError("usable_travel_from_switch_mm must contain measured XYZ distances")
    for axis in "XYZ":
        value = lengths.get(axis)
        if type(value) not in (float, int) or not math.isfinite(value) or value <= 3 * distance:
            raise ValueError(f"{axis}: set measured usable travel from switch (> {3 * distance} mm)")
    search, latch, final = (settings.get(k) for k in ("search_speed_mm_s", "latch_speed_mm_s", "return_speed_mm_s"))
    if not all(type(v) in (float, int) and math.isfinite(v) for v in (search, latch, final)) or not 0 < latch < search <= 5 or not 0 < final <= 5:
        raise ValueError("Require 0 < latch < search <= 5 and 0 < return <= 5 mm/s")
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("Output directory must be empty; existing machine configuration is never overwritten")
    source = ROOT / "linuxcnc/vendor-reference"
    ini = (source / "烛龙V2.ini").read_text()
    ini = ini.replace("[EMCMOT]", "[EMCMOT]\nHOMEMOD = zhulong_homing", 1)

    def update_section(text: str, section: str, values: dict) -> str:
        pattern = rf"(?ms)^\[{section}\]\s*\n(.*?)(?=^\[|\Z)"
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f"Missing INI section {section}")
        body = match.group(1)
        for key, value in values.items():
            body = re.sub(rf"(?m)^{key}\s*=.*\n?", "", body)
            body += f"{key} = {value}\n"
        return text[:match.start()] + f"[{section}]\n" + body + "\n" + text[match.end():]

    for joint, axis in enumerate("XYZ"):
        direction = board["homing"]["axes"][axis]["direction"]
        # Reserve one retreat distance at each physical end.
        span = lengths[axis] - 2 * distance
        limits = {"MIN_LIMIT": -span if direction > 0 else 0.0,
                  "MAX_LIMIT": 0.0 if direction > 0 else span}
        ini = update_section(ini, f"AXIS_{axis}", limits)
        ini = update_section(ini, f"JOINT_{joint}", {
            **limits, "HOME": 0.0, "HOME_OFFSET": direction * distance,
            "HOME_SEARCH_VEL": direction * search, "HOME_LATCH_VEL": direction * latch,
            "HOME_FINAL_VEL": final, "HOME_IGNORE_LIMITS": "YES", "HOME_USE_INDEX": "NO",
            "HOME_SEQUENCE": joint + 1,
        })
    # Rotary joints have no specified homing method; exclude from HOME ALL.
    for joint in range(3, 6):
        ini = update_section(ini, f"JOINT_{joint}", {"HOME_SEQUENCE": 101})
    hal = (source / "烛龙V2.hal").read_text()
    hal = hal.replace("loadrt hostmot2", "loadrt debounce cfg=3\nloadrt hostmot2", 1)
    hal = hal.replace("addf motion-command-handler", "addf debounce.0 servo-thread\naddf motion-command-handler", 1)
    extra = ["setp debounce.0.delay 5"]
    for joint, axis in enumerate("XYZ"):
        a = axis.lower()
        gpio = board["homing"]["axes"][axis]["gpio"]
        side = "pos" if board["homing"]["axes"][axis]["direction"] > 0 else "neg"
        input_pin = "in_not" if active_low else "in"
        hal = re.sub(rf"(?m)^net {a}-{side}-limit\s+=>\s+joint\.{joint}\.{side}-lim-sw-in.*$", "", hal)
        extra.extend([
            f"net {a}-home-raw hm2_7i92.0.gpio.{gpio:03}.{input_pin} => debounce.0.{joint}.in",
            f"net {a}-home-sw debounce.0.{joint}.out => joint.{joint}.{side}-lim-sw-in",
        ])
    destination.mkdir(parents=True, exist_ok=True)
    for file in source.iterdir():
        if file.is_file() and file.name not in ("烛龙V2.ini", "烛龙V2.hal"):
            shutil.copyfile(file, destination / file.name)
    (destination / "烛龙V2.ini").write_text(ini)
    (destination / "烛龙V2.hal").write_text(hal + "\n" + "\n".join(extra) + "\n")
    return destination / "烛龙V2.ini"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, default=ROOT / "linuxcnc/homing.json")
    parser.add_argument("--board", type=Path, default=BOARD_PATH)
    parser.add_argument("--output", type=Path, default=ROOT / ".build/linuxcnc")
    args = parser.parse_args()
    try:
        print(prepare(json.loads(args.settings.read_text()), args.output, board_path=args.board))
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(str(error)) from error
