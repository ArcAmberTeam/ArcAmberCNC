"""Received machining jobs through public Controller and real network/service seams."""

import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from test_controller import FakeClock, FakeLinuxCNC

from bettercnc_controller import Controller


def received(inbox, body=b"G21\nG90\nM2\n"):
    transfer_id = str(uuid.uuid4())
    inbox.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory = inbox / transfer_id
    directory.mkdir(mode=0o700)
    program = directory / "part.nc"
    program.write_bytes(body)
    program.chmod(0o600)
    receipt = directory / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "transferId": transfer_id,
                "filename": "part.nc",
                "size": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "state": "received",
            }
        )
    )
    receipt.chmod(0o600)
    return transfer_id


class ReceivedJobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/tmp", prefix="received-")
        self.addCleanup(self.temp.cleanup)
        self.inbox = Path(self.temp.name) / "inbox"
        self.transfer = received(self.inbox)
        self.module = FakeLinuxCNC()
        self.clock = FakeClock()
        self.controller = Controller(
            ini_path="/machine/machine.ini",
            module=self.module,
            clock=self.clock,
            cam_inbox=self.inbox,
        )
        self.addCleanup(self.controller.close)

    def running(self):
        self.controller.start_received(self.transfer)
        for _ in range(3):
            self.module.confirm(
                state=self.module.RCS_EXEC if self.module.calls[-1][0] == "auto" else None
            )
            self.controller.poll()
        self.assertEqual(self.module.calls[-1], ("auto", (self.module.AUTO_RUN, 0)))
        self.assertEqual(self.controller.received_status(self.transfer)["state"], "running")

    def finish(self):
        s = self.module.status
        s.interp_state = self.module.INTERP_IDLE
        s.state = self.module.RCS_DONE
        s.inpos = True
        s.queue = s.active_queue = 0
        self.controller.poll()

    def test_verified_file_loads_then_runs_and_completes_only_after_motion_done(self):
        self.running()
        s = self.module.status
        s.interp_state = self.module.INTERP_IDLE
        s.state = self.module.RCS_DONE
        s.inpos = False
        s.queue = 1
        self.controller.poll()
        self.assertEqual(self.controller.received_status(self.transfer)["state"], "running")
        self.finish()
        self.assertEqual(self.controller.received_status(self.transfer)["state"], "completed")
        calls = list(self.module.calls)
        self.controller.start_received(self.transfer)
        self.assertEqual(calls, self.module.calls)
        self.assertFalse(any(name == "mdi" for name, _ in calls))

    def test_received_content_is_snapshotted_before_load(self):
        record = self.controller.start_received(self.transfer)
        original = self.inbox / self.transfer / "part.nc"
        original.write_text("M2\n")
        self.assertEqual(Path(record["path"]).read_text(), "G21\nG90\nM2\n")
        self.assertEqual(self.module.calls[0], ("program_open", (record["path"],)))

    def test_offline_unhomed_estop_disabled_and_limit_override_never_issue_commands(self):
        for change in ("offline", "unhomed", "estop", "off", "limit"):
            with self.subTest(change=change):
                module = FakeLinuxCNC()
                if change == "offline":
                    module.available = False
                if change == "unhomed":
                    module.status.homed[0] = 0
                    module.ini_values[("TRAJ", "NO_FORCE_HOMING")] = "1"
                if change == "estop":
                    module.status.estop = True
                if change == "off":
                    module.status.enabled = False
                if change == "limit":
                    module.status.joint[0]["override_limits"] = True
                controller = Controller(
                    ini_path="/machine/machine.ini", module=module, cam_inbox=self.inbox
                )
                transfer = received(self.inbox)
                self.assertEqual(controller.start_received(transfer)["state"], "error")
                self.assertEqual(module.calls, [])
                controller.close()

    def test_corrupt_file_and_symlink_are_rejected_without_motion(self):
        (self.inbox / self.transfer / "part.nc").write_text("G0 X999\n")
        with self.assertRaises(ValueError):
            self.controller.start_received(self.transfer)
        self.assertEqual(self.module.calls, [])
        self.assertEqual(self.controller.received_status(self.transfer)["state"], "error")
        transfer = received(self.inbox)
        source = self.inbox / transfer / "part.nc"
        source.unlink()
        source.symlink_to(self.inbox / self.transfer / "part.nc")
        with self.assertRaises(ValueError):
            self.controller.start_received(transfer)
        self.assertEqual(self.module.calls, [])

    def test_restart_never_replays_an_incomplete_or_completed_job(self):
        self.running()
        other_module = FakeLinuxCNC()
        other = Controller(
            ini_path="/machine/machine.ini", module=other_module, cam_inbox=self.inbox
        )
        self.assertEqual(other.start_received(self.transfer)["state"], "unknown")
        self.assertEqual(other_module.calls, [])
        self.finish()
        self.assertEqual(other.start_received(self.transfer)["state"], "completed")
        self.assertEqual(other_module.calls, [])

    def test_stop_error_power_loss_and_foreign_writer_never_report_completion(self):
        for reason in ("stop", "error", "power", "foreign", "disconnect"):
            with self.subTest(reason=reason):
                if self.controller.received_status(self.transfer) is not None:
                    self.controller.close()
                    self.module = FakeLinuxCNC()
                    self.controller = Controller(
                        ini_path="/machine/machine.ini", module=self.module, cam_inbox=self.inbox
                    )
                    self.transfer = received(self.inbox)
                self.running()
                if reason == "stop":
                    self.controller.dispatch("program.stop")
                if reason == "error":
                    self.module.errors.append((self.module.NML_ERROR, "motion error"))
                if reason == "power":
                    self.module.status.enabled = False
                if reason == "foreign":
                    self.module.status.echo_serial_number += 10
                if reason == "disconnect":
                    self.module.available = False
                self.controller.poll()
                self.assertIn(
                    self.controller.received_status(self.transfer)["state"], ("unknown", "error")
                )


if __name__ == "__main__":
    unittest.main()
