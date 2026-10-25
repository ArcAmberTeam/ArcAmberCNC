"""HOME ALL completion and dedicated-machine interlocks via the public API."""

import os
import unittest
from unittest.mock import patch

from test_controller import FakeLinuxCNC

from bettercnc_controller import Controller


def six_joint_vendor():
    vendor = FakeLinuxCNC()
    vendor.ini_values[("KINS", "JOINTS")] = "6"
    vendor.ini_values[("KINS", "KINEMATICS")] = "trivkins coordinates=XYZABC"
    vendor.status.joints = 6
    vendor.status.axis_mask = 63
    vendor.status.homed = [0] * 6
    vendor.status.joint = [dict(vendor.status.joint[0]) for _ in range(6)]
    for joint in range(3):
        vendor.ini_values[(f"JOINT_{joint}", "HOME_SEQUENCE")] = str(joint + 1)
    for joint in range(3, 6):
        vendor.ini_values[(f"JOINT_{joint}", "HOME_SEQUENCE")] = "101"
    return vendor


def verified_profile(vendor):
    """Only a test fixture: these distances are never production commissioning data."""
    vendor.ini_values[("EMCMOT", "HOMEMOD")] = "zhulong_homing"
    vendor.ini_values[("TRAJ", "LINEAR_UNITS")] = "mm"
    vendor.ini_values[("BETTERCNC_HOMING", "PROFILE")] = "zhulong-v2"
    vendor.ini_values[("BETTERCNC_HOMING", "SWITCH_INPUTS_VERIFIED")] = "YES"
    for joint, axis, direction in ((0, "X", -1), (1, "Y", 1), (2, "Z", -1)):
        vendor.ini_values[("BETTERCNC_HOMING", f"TRAVEL_{axis}_MM")] = "100"
        values = {
            "HOME": "0",
            "HOME_OFFSET": str(direction * 5),
            "HOME_SEARCH_VEL": str(direction * 2),
            "HOME_LATCH_VEL": str(direction * 0.5),
            "HOME_FINAL_VEL": "2",
            "HOME_IGNORE_LIMITS": "YES",
            "HOME_USE_INDEX": "NO",
        }
        for key, value in values.items():
            vendor.ini_values[(f"JOINT_{joint}", key)] = value
        for section in ("AXIS_" + axis, f"JOINT_{joint}"):
            vendor.ini_values[(section, "MIN_LIMIT")] = "-90" if direction > 0 else "0"
            vendor.ini_values[(section, "MAX_LIMIT")] = "0" if direction > 0 else "90"


class HomingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"BETTERCNC_KIOSK": "0"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_home_all_finishes_when_only_configured_xyz_finish(self):
        vendor = six_joint_vendor()
        controller = Controller(module=vendor)
        self.assertTrue(controller.dispatch("machine.home-all"))
        self.assertEqual(vendor.calls, [("home", (-1,))])
        vendor.confirm(apply=False)
        vendor.status.homed = [1, 1, 0, 0, 0, 0]
        self.assertEqual(controller.poll()["commandState"], "sent")
        vendor.status.homed[2] = 1
        vendor.status.joint[2]["homing"] = True
        self.assertEqual(controller.poll()["commandState"], "sent")
        vendor.status.joint[2]["homing"] = False
        snapshot = controller.poll()
        self.assertEqual(snapshot["commandState"], "completed")
        self.assertEqual(snapshot["homeAllJoints"], [0, 1, 2])
        self.assertTrue(snapshot["homeAllHomed"])
        self.assertEqual(snapshot["homed"], [True, True, True, False, False, False])

    def test_omitted_sequences_and_synchronized_groups_match_native_home_all(self):
        vendor = six_joint_vendor()
        for joint in range(3, 6):
            del vendor.ini_values[(f"JOINT_{joint}", "HOME_SEQUENCE")]
        vendor.ini_values[("JOINT_0", "HOME_SEQUENCE")] = "-1"
        vendor.ini_values[("JOINT_1", "HOME_SEQUENCE")] = "1"
        vendor.ini_values[("JOINT_2", "HOME_SEQUENCE")] = "2"
        controller = Controller(module=vendor)
        self.assertFalse(controller.dispatch("machine.home-X"))
        self.assertTrue(controller.dispatch("machine.home-all"))
        vendor.confirm(apply=False)
        vendor.status.homed[:3] = [1, 1, 1]
        self.assertEqual(controller.poll()["commandState"], "completed")

    def test_empty_or_gapped_home_all_is_rejected_before_native_commands(self):
        for sequences in ((101, 101, 101), (1, 3, 4), (-101, 1, 2)):
            with self.subTest(sequences=sequences):
                vendor = FakeLinuxCNC()
                for joint, sequence in enumerate(sequences):
                    vendor.ini_values[(f"JOINT_{joint}", "HOME_SEQUENCE")] = str(sequence)
                controller = Controller(module=vendor)
                self.assertFalse(controller.dispatch("machine.home-all"))
                self.assertFalse(controller.snapshot["capabilities"]["machine.home-all"])
                self.assertEqual(vendor.calls, [])

    def test_xyz_completion_does_not_authorize_any_coordinated_motion(self):
        vendor = six_joint_vendor()
        verified_profile(vendor)
        vendor.status.homed = [1, 1, 1, 0, 0, 0]
        controller = Controller(module=vendor)
        for action, payload in (
            ("mdi.execute", {"text": "G0 A1"}),
            ("mdi.execute", {"text": "G0 X1"}),
            ("machine.mode", {"mode": "mdi"}),
            ("program.run", {}),
            ("mode.world", {}),
        ):
            with self.subTest(action=action):
                self.assertFalse(controller.dispatch(action, payload))
        vendor.status.motion_mode = vendor.TRAJ_MODE_TELEOP
        self.assertFalse(
            controller.dispatch(
                "jog.start", {"axis": "X", "mode": "world", "direction": 1, "velocity": 1}
            )
        )
        snapshot = controller.poll()
        self.assertTrue(snapshot["homeAllHomed"])
        for name in ("mdi.execute", "program.run", "mode.world", "jog.start"):
            self.assertFalse(snapshot["capabilities"][name])
        self.assertEqual(vendor.calls, [])

    def test_dedicated_home_requires_verified_measurements_and_effective_parameters(self):
        cases = (
            (("BETTERCNC_HOMING", "TRAVEL_X_MM"), None),
            (("BETTERCNC_HOMING", "TRAVEL_Y_MM"), "5"),
            (("BETTERCNC_HOMING", "TRAVEL_Z_MM"), "15"),
            (("BETTERCNC_HOMING", "SWITCH_INPUTS_VERIFIED"), "NO"),
            (("EMCMOT", "HOMEMOD"), "homemod"),
            (("TRAJ", "LINEAR_UNITS"), "inch"),
            (("JOINT_0", "HOME_OFFSET"), "0"),
            (("JOINT_1", "HOME_SEARCH_VEL"), "-2"),
            (("JOINT_2", "HOME_LATCH_VEL"), "0"),
            (("JOINT_0", "MAX_LIMIT"), "100"),
            (("JOINT_3", "HOME_SEQUENCE"), "4"),
        )
        for setting, value in cases:
            with self.subTest(setting=setting, value=value):
                vendor = six_joint_vendor()
                verified_profile(vendor)
                if value is None:
                    del vendor.ini_values[setting]
                else:
                    vendor.ini_values[setting] = value
                controller = Controller(module=vendor)
                self.assertFalse(controller.dispatch("machine.home-all"))
                self.assertFalse(controller.dispatch("machine.home-X"))
                self.assertFalse(controller.dispatch("home", {"joint": 0}))
                self.assertIn("回零未配置", controller.snapshot["commandMessage"])
                self.assertFalse(controller.snapshot["capabilities"]["machine.home-all"])
                self.assertEqual(vendor.calls, [])

    def test_verified_dedicated_profile_homes_xyz_but_never_immediate_homes_abc(self):
        vendor = six_joint_vendor()
        verified_profile(vendor)
        controller = Controller(module=vendor)
        self.assertFalse(controller.dispatch("machine.home-A"))
        self.assertFalse(controller.dispatch("home", {"joint": 4}))
        self.assertEqual(vendor.calls, [])
        self.assertTrue(controller.dispatch("machine.home-X"))
        self.assertEqual(vendor.calls, [("home", (0,))])
        self.assertFalse(controller.snapshot["capabilities"]["machine.home-A"])

    def test_kiosk_legacy_instant_homing_and_no_force_bypass_are_blocked(self):
        with patch.dict(os.environ, {"BETTERCNC_KIOSK": "1"}):
            vendor = FakeLinuxCNC()
            vendor.ini_values[("TRAJ", "NO_FORCE_HOMING")] = "1"
            vendor.status.homed = [0, 0, 0]
            controller = Controller(module=vendor)
            self.assertFalse(controller.dispatch("machine.home-all"))
            self.assertFalse(controller.dispatch("mdi.execute", {"text": "G0 X1"}))
            self.assertEqual(vendor.calls, [])
        vendor = FakeLinuxCNC()
        controller = Controller(module=vendor)
        self.assertTrue(controller.dispatch("machine.home-all"))
        self.assertEqual(vendor.calls, [("home", (-1,))])

    def test_unhome_all_still_waits_for_every_joint(self):
        vendor = six_joint_vendor()
        verified_profile(vendor)
        vendor.status.homed = [1] * 6
        controller = Controller(module=vendor)
        self.assertTrue(controller.dispatch("machine.unhome-all"))
        vendor.confirm(apply=False)
        vendor.status.homed[:3] = [0, 0, 0]
        self.assertEqual(controller.poll()["commandState"], "sent")
        vendor.status.homed[3:] = [0, 0, 0]
        self.assertEqual(controller.poll()["commandState"], "completed")


if __name__ == "__main__":
    unittest.main()
