"""Exercise configuration CI through its CLI; no machine processes are run."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECKER = Path(__file__).resolve().parents[1] / "check-configs.py"


class ConfigChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.folder = self.root / "configs/machine"
        self.folder.mkdir(parents=True)

    def write(self, name, text):
        path = self.folder / name
        path.write_text(text)
        return path

    def run_check(self):
        return subprocess.run(
            [sys.executable, str(CHECKER), "--root", str(self.root)],
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
        )

    def test_duplicate_hal_files_continuations_and_library_paths(self):
        self.write(
            "machine.ini", "[HAL]\nHALFILE = first.hal\nHALFILE = LIB:second.hal\n"
        )
        self.write(
            "first.hal",
            "net enable motion.motion-enabled \\\n  => drive.enable\nnet existing-signal\nloadrt [KINS]KINEMATICS\n",
        )
        library = self.root / "lib/hallib"
        library.mkdir(parents=True)
        (library / "second.hal").write_text("setp example.param 1\n")
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_local_reference_fails(self):
        self.write("machine.ini", "[HAL]\nHALFILE = missing.hal\n")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing local reference", result.stdout)

    def test_invalid_hal_command_and_quotes_fail(self):
        self.write("broken.hal", 'setp only-one-argument\nnet signal "unterminated\n')
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("too few arguments", result.stdout)
        self.assertIn("No closing quotation", result.stdout)

    def test_include_cycles_and_invalid_included_assignments_fail(self):
        self.write("machine.ini", "#INCLUDE child.inc\n[HAL]\n")
        self.write("child.inc", "#INCLUDE machine.ini\n[BAD]\nno assignment\n")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("include cycle", result.stdout)
        self.assertIn("invalid INI assignment", result.stdout)

    def test_tcl_is_parsed_but_never_executed(self):
        marker = self.root / "must-not-exist"
        path = self.write("wiring.tcl", f"exec touch {marker}\nloadrt motmod\n")
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(marker.exists())
        path.write_text("if {1} {\n")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incomplete Tcl syntax", result.stdout)

    def test_baseline_cannot_hide_changes_or_stay_after_a_fix(self):
        path = self.write("old.hal", "setp broken\n")
        diagnostic = "configs/machine/old.hal:1: too few arguments: setp broken"
        baseline = self.root / ".github/ci/config-baseline.json"
        baseline.parent.mkdir(parents=True)
        baseline.write_text(
            json.dumps(
                {
                    diagnostic: {
                        "reason": "Historical fixture",
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                }
            )
        )
        self.assertEqual(self.run_check().returncode, 0)
        path.write_text("setp broken\n# modified file\n")
        self.assertNotEqual(self.run_check().returncode, 0)
        path.write_text("setp fixed 1\n")
        self.assertNotEqual(self.run_check().returncode, 0)
        baseline.write_text("{}")
        self.assertEqual(self.run_check().returncode, 0)


if __name__ == "__main__":
    unittest.main()
