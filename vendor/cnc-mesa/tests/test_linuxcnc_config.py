import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("machine_config", ROOT / "linuxcnc/prepare.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class ConfigTests(unittest.TestCase):
    def settings(self):
        settings = json.loads((ROOT / "linuxcnc/homing.json").read_text())
        # Synthetic commissioning data, never measured machine dimensions.
        settings["switch_inputs_verified"] = True
        settings["usable_travel_from_switch_mm"] = dict.fromkeys("XYZ", 200)
        return settings

    def assert_rejected(self, settings):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config"
            with self.assertRaises(ValueError):
                builder.prepare(settings, target)
            self.assertFalse(target.exists())

    def test_unknown_or_insufficient_travel_does_not_emit_runtime_config(self):
        for axis in "XYZ":
            for value in (None, True, -1, 0, 5, 10, 15, float("nan"), float("inf")):
                with self.subTest(axis=axis, value=value):
                    settings = self.settings()
                    settings["usable_travel_from_switch_mm"][axis] = value
                    self.assert_rejected(settings)

    def test_all_switches_must_be_verified_before_emitting_a_runtime_profile(self):
        for value in (False, None, 1, "true"):
            with self.subTest(value=value):
                settings = self.settings()
                settings["switch_inputs_verified"] = value
                self.assert_rejected(settings)

    def test_invalid_speeds_are_rejected_before_writing(self):
        for key in ("search_speed_mm_s", "latch_speed_mm_s", "return_speed_mm_s"):
            for value in (True, None, 0, -1, 6, float("nan"), float("inf")):
                with self.subTest(key=key, value=value):
                    settings = self.settings()
                    settings[key] = value
                    self.assert_rejected(settings)
        settings = self.settings()
        settings["latch_speed_mm_s"] = settings["search_speed_mm_s"]
        self.assert_rejected(settings)

    def test_missing_settings_are_rejected_before_writing(self):
        for key in self.settings():
            with self.subTest(key=key):
                settings = self.settings()
                del settings[key]
                self.assert_rejected(settings)
        settings = self.settings()
        del settings["usable_travel_from_switch_mm"]["Z"]
        self.assert_rejected(settings)

    def test_nc_profile_wires_active_high_inputs_to_home_and_directional_limits(self):
        settings = self.settings()
        with tempfile.TemporaryDirectory() as directory:
            path = builder.prepare(settings, Path(directory))
            ini = path.read_text()
            hal = (path.parent / "烛龙V2.hal").read_text()
            self.assertIn("HOMEMOD = zhulong_homing", ini)
            for j, axis in enumerate("XYZ"):
                section = ini.split(f"[JOINT_{j}]")[1].split("[")[0]
                direction = 1 if axis == "Y" else -1
                self.assertIn(f"HOME_OFFSET = {direction * 5}", section)
                self.assertIn(f"HOME_SEARCH_VEL = {direction * 2.0}", section)
                self.assertIn(f"HOME_LATCH_VEL = {direction * 0.5}", section)
                self.assertIn("HOME = 0.0", section)
                self.assertIn("HOME_FINAL_VEL = 2.0", section)
                self.assertIn(f"HOME_SEQUENCE = {j + 1}", section)
                self.assertIn(f"MIN_LIMIT = {-190 if direction > 0 else 0.0}", section)
                self.assertIn(f"MAX_LIMIT = {0.0 if direction > 0 else 190}", section)
                self.assertIn(f"gpio.{20+j:03}.in => debounce.0.{j}.in", hal)
                self.assertNotIn(f"gpio.{20+j:03}.in_not", hal)
                a = axis.lower()
                side = "pos" if direction > 0 else "neg"
                self.assertIn(f"net {a}-home-sw     =>  joint.{j}.home-sw-in", hal)
                self.assertIn(f"net {a}-home-sw debounce.0.{j}.out => joint.{j}.{side}-lim-sw-in", hal)
                self.assertNotIn(f"net {a}-{side}-limit", hal)
            for j in range(3, 6):
                section = ini.split(f"[JOINT_{j}]")[1].split("[")[0]
                self.assertIn("HOME_SEQUENCE = 101", section)
            self.assertIn("setp debounce.0.delay 5", hal)
            self.assertLess(hal.index("addf hm2_7i92.0.read"), hal.index("addf debounce.0"))
            self.assertLess(hal.index("addf debounce.0"), hal.index("addf motion-command-handler"))
            self.assertLess(hal.index("addf debounce.0"), hal.index("addf motion-controller"))

    def test_profile_polarity_controls_the_selected_hostmot2_input(self):
        for active_low in (False, True):
            with self.subTest(active_low=active_low), tempfile.TemporaryDirectory() as directory:
                board = json.loads(builder.BOARD_PATH.read_text())
                board["homing"]["active_low"] = active_low
                profile = Path(directory) / "board.json"
                profile.write_text(json.dumps(board))
                path = builder.prepare(self.settings(), Path(directory) / "config", board_path=profile)
                hal = (path.parent / "烛龙V2.hal").read_text()
                suffix = "in_not" if active_low else "in"
                for j in range(3):
                    self.assertIn(f"gpio.{20+j:03}.{suffix} => debounce.0.{j}.in", hal)

    def test_invalid_board_contract_does_not_emit_a_profile(self):
        invalid = ({"active_low": "false"}, {"distance_mm": True}, {"distance_mm": 0},
                   {"distance_mm": float("inf")},
                   {"axes": {"X": {"gpio": 20, "direction": 1}}})
        for overrides in invalid:
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory() as directory:
                board = json.loads(builder.BOARD_PATH.read_text())
                board["homing"].update(overrides)
                profile = Path(directory) / "board.json"
                profile.write_text(json.dumps(board))
                target = Path(directory) / "config"
                with self.assertRaises(ValueError):
                    builder.prepare(self.settings(), target, board_path=profile)
                self.assertFalse(target.exists())

    def test_existing_machine_configuration_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            existing = target / "烛龙V2.ini"
            existing.write_text("site-specific machine configuration")
            with self.assertRaisesRegex(ValueError, "never overwritten"):
                builder.prepare(self.settings(), target)
            self.assertEqual(existing.read_text(), "site-specific machine configuration")
            self.assertEqual(list(target.iterdir()), [existing])

    def test_cli_accepts_explicit_settings_and_refuses_repeat_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory) / "settings.json"
            settings.write_text(json.dumps(self.settings()))
            target = Path(directory) / "config"
            command = [sys.executable, str(ROOT / "linuxcnc/prepare.py"),
                       "--settings", str(settings), "--output", str(target)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()), target / "烛龙V2.ini")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("never overwritten", result.stderr)
