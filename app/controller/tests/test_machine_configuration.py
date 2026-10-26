"""Read machine configuration through the public observer only."""

import unittest

from test_controller import FakeLinuxCNC

from bettercnc_controller import StatusReader


class MachineConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.vendor = FakeLinuxCNC()
        self.vendor.command = self.vendor.error_channel = self.forbidden_channel
        self.reader = StatusReader(module=self.vendor, ini_path="/machine/machine.ini")
        self.vendor.ini_values.update(
            {
                ("AXIS_X", "MIN_LIMIT"): "-0.1",
                ("AXIS_X", "MAX_LIMIT"): "410",
                ("AXIS_B", "MIN_LIMIT"): "-90",
                ("AXIS_B", "MAX_LIMIT"): "90",
                ("AXIS_B", "MAX_VELOCITY"): "10",
            }
        )

    def forbidden_channel(self):
        self.fail("configuration read opened a command or error channel")

    def test_active_axes_ignore_reserved_sections_and_joint_count(self):
        self.vendor.status.joints = 5
        config = self.reader.poll()["configuration"]
        self.assertEqual([axis["name"] for axis in config["axes"]], list("XYZ"))
        self.assertEqual(config["axes"][0]["min"], -0.1)
        self.assertEqual(config["axes"][0]["max"], 410)
        self.assertEqual(config["axes"][0]["maxVelocity"], 1500)
        self.assertIsNone(config["axes"][1]["min"])
        self.assertEqual(config["kinematics"], "trivkins coordinates=XYZ")
        self.assertEqual(self.vendor.calls, [])

    def test_four_and_five_axis_names_are_preserved_without_guessed_kinematics(self):
        for mask, names in ((23, "XYZB"), (47, "XYZAC")):
            self.vendor.status.axis_mask = mask
            config = self.reader.poll()["configuration"]
            self.assertEqual([axis["name"] for axis in config["axes"]], list(names))
            for axis in config["axes"][3:]:
                self.assertEqual(axis["kind"], "rotary")
                self.assertEqual(axis["unit"], "deg")

    def test_units_are_converted_to_mm_degrees_and_per_minute(self):
        self.vendor.status.axis_mask = 23
        self.vendor.status.linear_units = 1 / 25.4
        self.vendor.status.angular_units = 2
        axes = self.reader.poll()["configuration"]["axes"]
        self.assertAlmostEqual(axes[0]["max"], 410 * 25.4)
        self.assertAlmostEqual(axes[0]["maxVelocity"], 1500 * 25.4)
        self.assertEqual((axes[3]["min"], axes[3]["max"]), (-45, 45))
        self.assertEqual(axes[3]["maxVelocity"], 300)

    def test_invalid_and_missing_configuration_remain_unknown(self):
        self.vendor.ini_values[("AXIS_X", "MIN_LIMIT")] = "nan"
        self.assertIsNone(self.reader.poll()["configuration"]["axes"][0]["min"])
        self.vendor.ini_values[("AXIS_X", "MIN_LIMIT")] = "999"
        self.assertIsNone(self.reader.poll()["configuration"]["axes"][0]["max"])
        self.vendor.ini_values[("AXIS_X", "MIN_LIMIT")] = "-1e308"
        self.vendor.ini_values[("AXIS_X", "MAX_LIMIT")] = "1e308"
        self.assertIsNone(self.reader.poll()["configuration"]["axes"][0]["max"])
        self.vendor.status.ini_filename = None
        reader = StatusReader(module=self.vendor)
        status = reader.poll()
        self.assertTrue(status["connected"])
        self.assertIsNone(status["configuration"])

    def test_disconnect_clears_configuration_and_reconnect_reads_fresh_values(self):
        self.assertIsNotNone(self.reader.poll()["configuration"])
        self.vendor.available = False
        self.assertIsNone(self.reader.poll()["configuration"])
        self.vendor.available = True
        self.vendor.ini_values[("AXIS_X", "MAX_LIMIT")] = "400"
        self.assertEqual(self.reader.poll()["configuration"]["axes"][0]["max"], 400)
