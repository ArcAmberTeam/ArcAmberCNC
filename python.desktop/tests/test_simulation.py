"""Public controller and desktop/service socket tests with only vendor seams replaced."""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "python.desktop/python"), str(ROOT / "python.service/src")]

from PySide6.QtCore import QSettings
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from bettercnc.desktop import DesktopBackend
from bettercnc.session import SessionClient, read_machine_status
from bettercnc_controller import Controller
from interactive.linear_program import read_linear_program
from interactive.service_host import ServiceHost, write_configuration
from interactive.vendor import LinuxCNCInterface

SAMPLE = Path(__file__).parent / "programs/rectangle-demo.ngc"


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.now = 0.0
        self.vendor = LinuxCNCInterface(write_configuration(folder.name), clock=lambda: self.now)
        self.controller = Controller(module=self.vendor, clock=lambda: self.now)
        self.addCleanup(self.controller.close)
        self.tick()

    def tick(self, seconds=0.05):
        for _ in range(max(1, round(seconds / .05))):
            self.now += .05
            self.controller.poll()
        return self.controller.snapshot

    def command(self, action, payload=None):
        self.assertTrue(self.controller.dispatch(action, payload or {}), self.controller.snapshot)
        for _ in range(100):
            s = self.tick()
            if s["commandState"] == "completed":
                return s
            self.assertNotIn(s["commandState"], ("error", "unknown"), s)
        self.fail(f"No acknowledgement: {action}")

    def prepare(self):
        self.command("machine.estop")
        self.command("machine.power")
        self.command("machine.home-all")
        self.command("file.open", {"path": str(SAMPLE.resolve())})

    def test_rectangle_geometry_and_unsupported_input(self):
        data = read_linear_program(SAMPLE)
        self.assertEqual(data["bounds"], {"min": [0, 0, -1], "max": [40, 30, 5]})
        self.assertEqual([s["end"] for s in data["segments"]],
                         [[0, 0, -1], [40, 0, -1], [40, 30, -1], [0, 30, -1], [0, 0, -1], [0, 0, 5]])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.ngc"
            source = SAMPLE.read_text()
            cases = [source.replace("G1 X40 Y30", command) for command in
                     ("G2 X40 Y30 I0 J15", "G91 X40", "G20", "G1 X#1", "G1 X1 X2", "G0 G1 X2", "G1 F0 X1", "T1 M6")]
            cases += [source.replace("G21", ""), source.replace("M2", ""), source + "G0 X1\n"]
            for text in cases:
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    read_linear_program(path)

    def test_delayed_ack_and_homing_are_observed_not_assumed(self):
        self.assertFalse(self.controller.dispatch("program.run", {}))
        self.assertTrue(self.controller.dispatch("machine.estop", {}))
        self.assertEqual(self.controller.snapshot["commandState"], "sent")
        self.assertTrue(self.controller.snapshot["estop"])
        self.assertTrue(self.tick()["estop"])
        self.assertFalse(self.tick(.2)["estop"])
        self.command("machine.power")
        self.assertTrue(self.controller.dispatch("machine.home-all", {}))
        s = self.tick(.25)
        self.assertTrue(s["busy"])
        self.assertEqual(s["homed"], [False]*3)
        self.assertEqual(s["commandState"], "sent")
        s = self.tick(1.2)
        self.assertEqual(s["homed"], [True]*3)
        self.assertEqual(s["commandState"], "completed")

    def test_pause_resume_stop_and_complete(self):
        self.prepare()
        self.command("program.run")
        self.tick(12)
        self.assertGreater(self.controller.snapshot["actualPosition"][0], 0)
        self.command("program.pause")
        position = self.controller.snapshot["actualPosition"]
        self.assertEqual(self.tick(10)["actualPosition"], position)
        self.command("program.resume")
        self.assertNotEqual(self.tick(2)["actualPosition"], position)
        self.command("program.stop")
        position = self.controller.snapshot["actualPosition"]
        self.assertEqual(self.tick(2)["actualPosition"], position)
        self.command("program.run")
        s = self.tick(60)
        self.assertFalse(s["busy"])
        self.assertEqual(s["actualPosition"][:3], [0, 0, 5])
        self.assertEqual(s["spindleSpeed"], 0)
        self.assertEqual(self.vendor.diagnostics()["status"], "已完成")

    def test_single_step_pauses_after_each_block(self):
        self.prepare()
        self.command("program.step")
        s = self.tick(2)
        self.assertTrue(s["paused"])
        self.assertEqual(s["currentLine"], 5)
        self.command("program.step")
        self.assertEqual(self.tick(2)["currentLine"], 6)

    def test_restart_preserves_axes_not_named_in_block(self):
        self.prepare()
        self.command("program.run")
        self.tick(12)
        self.command("program.stop")
        stopped = self.controller.snapshot["actualPosition"][:3]
        self.assertGreater(stopped[0], 0)
        # First three modal blocks and G0 Z5 must retain the stopped X/Y.
        for _ in range(4):
            self.command("program.step")
            self.tick(2)
            self.assertEqual(self.controller.snapshot["actualPosition"][:2], stopped[:2])
        self.assertEqual(self.controller.snapshot["actualPosition"][2], 5)

    def test_external_estop_stops_motion_and_requires_power_again(self):
        self.prepare()
        self.command("program.run")
        self.tick(12)
        self.vendor.inject("estop")
        s = self.tick()
        position = s["actualPosition"]
        self.assertTrue(s["estop"])
        self.assertFalse(s["powered"])
        self.assertFalse(self.controller.dispatch("program.run", {}))
        self.assertEqual(self.tick(5)["actualPosition"], position)
        self.command("machine.estop")
        self.assertFalse(self.controller.snapshot["powered"])
        self.command("machine.power")
        self.assertTrue(self.controller.snapshot["capabilities"]["program.run"])

    def test_disconnect_cancels_unsent_steps_without_replay(self):
        self.prepare()
        self.assertTrue(self.controller.dispatch("program.run", {}))
        # Only mode(AUTO) has been sent; AUTO_RUN must not be replayed.
        self.vendor.inject("connection", False)
        self.assertFalse(self.tick(.3)["connected"])
        self.vendor.inject("connection", True)
        s = self.tick(1)
        self.assertTrue(s["connected"])
        self.assertEqual(s["commandState"], "unknown")
        self.assertFalse(s["busy"])
        events = self.vendor.diagnostics()["events"]
        self.assertFalse(any(e.get("method") == "auto" for e in events))

    def test_jog_stop_and_feed_override(self):
        self.prepare()
        self.command("jog.start", {"axis": "X", "direction": 1, "velocity": 2, "increment": 0})
        self.tick(1)
        self.controller.stop_jog()
        self.tick(.3)
        position = self.controller.snapshot["actualPosition"]
        self.assertGreater(position[0], 1)
        self.assertEqual(self.tick(2)["actualPosition"], position)
        self.command("program.run")
        self.tick(10)
        self.command("override.feed", {"value": 0})
        position = self.controller.snapshot["actualPosition"]
        self.assertEqual(self.tick(2)["actualPosition"], position)
        self.command("override.feed", {"value": 1})
        self.assertNotEqual(self.tick(1)["actualPosition"], position)

    def test_error_channel_and_unsupported_mdi(self):
        self.prepare()
        self.assertTrue(self.controller.dispatch("mdi.execute", {"text": "G0 X10"}))
        s = self.tick(1)
        self.assertEqual(s["commandState"], "error")
        self.assertIn("未实现 mdi", s["errors"][-1]["message"])
        self.command("program.run")
        self.tick(12)
        self.vendor.inject("error")
        s = self.tick()
        self.assertFalse(s["busy"])
        self.assertIn("伺服驱动报警", s["errors"][-1]["message"])


class SocketIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def wait(self, predicate, timeout=6):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            QTest.qWait(20)
        self.assertTrue(predicate(), self.desktop.snapshot)

    def test_readonly_probe_preserves_existing_gui_control_session(self):
        host = ServiceHost().start()
        self.addCleanup(host.close)
        owner = SessionClient(host.socket, ini_path=host.ini)
        self.addCleanup(owner.close)
        self.assertTrue(owner.poll()["connected"])
        self.assertTrue(read_machine_status(host.socket)["connected"])
        self.assertTrue(owner.poll()["connected"])
        host.vendor.inject("connection", False)
        self.assertFalse(read_machine_status(host.socket)["connected"])
        host.vendor.inject("connection", True)
        self.assertTrue(owner.poll()["connected"])

    def test_original_desktop_and_service_end_to_end(self):
        host = ServiceHost().start()
        self.addCleanup(host.close)
        self.desktop = DesktopBackend(socket_path=str(host.socket), ini_path=str(host.ini),
            settings=QSettings(str(host.folder / "settings.ini"), QSettings.Format.IniFormat))
        self.addCleanup(self.desktop.close)
        b = self.desktop
        self.wait(lambda: b.snapshot.get("connected"))
        self.assertEqual(host.socket.stat().st_mode & 0o777, 0o600)
        self.assertFalse(b.snapshot["capabilities"]["program.run"])
        b.openProgram(str(SAMPLE.resolve()))
        self.wait(lambda: b.snapshot.get("file") == str(SAMPLE.resolve()) and len(b.program.segments) == 6)
        self.assertTrue(b.program.previewWarnings)
        for action, predicate in [
            ("machine.estop", lambda: not b.snapshot["estop"]),
            ("machine.power", lambda: b.snapshot["powered"]),
            ("machine.home-all", lambda: all(b.snapshot["homed"]))]:
            self.wait(lambda: b.snapshot["commandState"] not in ("pending", "sent"))
            b.dispatch(action, {})
            self.wait(predicate)
        self.wait(lambda: b.snapshot["capabilities"]["program.run"])
        host.vendor.inject("rate", 10)
        b.dispatch("program.run", {})
        self.wait(lambda: b.snapshot["actualPosition"][0] > 2)
        b.dispatch("program.pause", {})
        self.wait(lambda: b.snapshot["paused"])
        position = b.snapshot["actualPosition"]
        QTest.qWait(300)
        self.assertEqual(b.snapshot["actualPosition"], position)
        b.dispatch("program.resume", {})
        self.wait(lambda: host.vendor.diagnostics()["status"] == "已完成")
        self.wait(lambda: not b.snapshot["busy"])
        self.assertEqual(b.snapshot["actualPosition"][:3], [0, 0, 5])
        host.vendor.inject("connection", False)
        self.wait(lambda: not b.snapshot["connected"])
        self.assertIsNone(b.snapshot["actualPosition"])
        host.vendor.inject("connection", True)
        self.wait(lambda: b.snapshot["connected"])
        host.vendor.inject("error")
        self.wait(lambda: any("伺服驱动报警" in e["message"] for e in b.snapshot["errors"]))
        report = ROOT / "python.desktop/artifacts/simulation/socket-test-report.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({"vendor": host.vendor.diagnostics(), "desktop": b.snapshot},
                                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    unittest.main()
