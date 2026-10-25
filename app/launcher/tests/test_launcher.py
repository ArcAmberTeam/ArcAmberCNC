"""Installed public CLI with real child processes and Unix observer protocol."""

import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="launch-", dir="/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        source = Path(__file__).with_name("process_fixture.py")
        for name in (
            "linuxcnc",
            "betterlinuxcnc",
            "betterlinuxcnc-service",
            "betterlinuxcnc-cam-link",
        ):
            path = self.bin / name
            path.write_text(
                f"#!{sys.executable}\n"
                f"exec(compile(open({str(source)!r}).read(), {str(source)!r}, 'exec'))\n"
            )
            path.chmod(0o700)
        self.ini = self.root / "机床 参数.ini"
        self.ini.write_text(
            "[DISPLAY]\nDISPLAY = betterlinuxcnc\n"
            "[HAL]\nHALFILE = first.hal\nHALFILE = second.hal\n"
        )
        self.token = self.root / "token"
        self.token.write_text("test-token-" * 5)
        self.token.chmod(0o600)
        self.config = self.root / "launcher.json"
        self.data = {
            "ini": self.ini.name,
            "startup_timeout": 2,
            "shutdown_timeout": 1,
            "cam": {"inbox": "inbox", "token_file": "token", "auto_run": True},
        }
        self.write_config()
        (self.root / "machine.json").write_text(
            json.dumps(
                {"programState": "idle", "queueDepth": 0, "activeQueueDepth": 0, "paused": False}
            )
        )
        self.env = dict(
            os.environ,
            PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
            XDG_RUNTIME_DIR=str(self.root / "run"),
            FIXTURE_ROOT=str(self.root),
        )
        self.env.pop("PYTHONPATH", None)
        self.env.pop("BETTERCNC_LOG_ROOT", None)
        self.processes = []
        self.addCleanup(self.cleanup_processes)

    def write_config(self):
        self.config.write_text(json.dumps(self.data, ensure_ascii=False))

    def events(self):
        path = self.root / "events"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def cleanup_processes(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if process.stdout:
                process.stdout.close()
        # Failure cases deliberately leave native/controller children alive.
        # These are only the executable fixtures created by this test case.
        for record in self.events():
            if record["event"] == "start":
                try:
                    os.kill(record["pid"], signal.SIGTERM)
                except ProcessLookupError:
                    pass
        expected = {e["pid"] for e in self.events() if e["event"] == "start"}
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            exited = {e["pid"] for e in self.events() if e["event"] == "exit"}
            if expected <= exited:
                break
            time.sleep(0.02)

    def launch(self, *args, cwd=None, keep_alive=False, **overrides):
        flags = [] if keep_alive else ["--once"]
        process = subprocess.Popen(
            [sys.executable, "-m", "bettercnc_launcher", *flags, *args],
            cwd=cwd or self.root,
            env=dict(self.env, **overrides),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.processes.append(process)
        return process

    def wait(self, predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() >= deadline:
                self.fail(f"fixture timeout; events={self.events()}")
            time.sleep(0.02)

    def ready(self):
        self.wait(
            lambda: any(
                json.loads(path.read_text())["phase"] == "ready"
                for path in self.root.glob(".runtime/launcher/*/state.json")
            )
        )

    def output(self, process):
        return process.communicate(timeout=5)[0]

    def test_check_uses_project_config_relative_paths_and_has_no_process_side_effects(self):
        original = self.ini.read_bytes()
        process = self.launch("--check", "--config", str(self.config), cwd=self.root.parent)
        plan = json.loads(self.output(process))
        self.assertEqual(process.returncode, 0)
        self.assertEqual(plan["ini"], str(self.ini.resolve()))
        self.assertEqual(plan["logRoot"], str(self.root.resolve() / ".runtime/launcher"))
        self.assertEqual(plan["commands"][1][-1], str(self.ini.resolve()))
        self.assertIn("--cam-inbox", plan["commands"][0])
        self.assertIn("--auto-run", plan["commands"][2])
        self.assertNotIn(self.token.read_text(), json.dumps(plan))
        self.assertEqual(self.events(), [])
        self.assertFalse((self.root / "run").exists())
        self.assertEqual(self.ini.read_bytes(), original)

    def test_lan_direct_mode_needs_no_token_or_certificate_configuration(self):
        self.data["cam"] = {"host": "0.0.0.0", "inbox": "inbox"}
        self.write_config()
        process = self.launch("--check")
        plan = json.loads(self.output(process))
        self.assertEqual(process.returncode, 0)
        self.assertNotIn("--token-file", plan["commands"][2])
        self.assertNotIn("--cert", plan["commands"][2])
        self.assertNotIn("--auto-run", plan["commands"][2])

    def test_startup_order_same_ini_read_only_protocol_and_reverse_normal_cleanup(self):
        process = self.launch()
        self.ready()
        starts = [event for event in self.events() if event["event"] == "start"]
        self.assertEqual(
            [event["role"] for event in starts],
            ["betterlinuxcnc-service", "linuxcnc", "betterlinuxcnc", "betterlinuxcnc-cam-link"],
        )
        self.assertEqual(starts[1]["argv"], [str(self.ini.resolve())])
        self.assertEqual(starts[2]["argv"], ["-ini", str(self.ini.resolve())])
        self.assertEqual(starts[2]["managed"], "1")
        self.assertEqual(starts[0]["socket"], starts[2]["socket"])
        (self.root / "quit-native").touch()
        output = self.output(process)
        self.assertEqual(process.returncode, 0, output)
        self.assertIn("启动编排完成", output)
        self.assertTrue(
            all(e["method"] == "machine.status" for e in self.events() if e["event"] == "request")
        )
        stopped = [e["role"] for e in self.events() if e["event"] == "stop"]
        self.assertLess(
            stopped.index("betterlinuxcnc-cam-link"), stopped.index("betterlinuxcnc-service")
        )
        for log in self.root.glob(".runtime/launcher/*/*.log"):
            self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o600)
            self.assertNotIn(self.token.read_text(), log.read_text())

    def test_signal_idle_uses_native_cleanup_before_controller_shutdown(self):
        process = self.launch()
        self.ready()
        process.send_signal(signal.SIGTERM)
        output = self.output(process)
        self.assertEqual(process.returncode, 0, output)
        events = self.events()
        native_end = next(i for i, e in enumerate(events) if e["event"] == "native-cleanup")
        service_end = next(
            i
            for i, e in enumerate(events)
            if e["role"] == "betterlinuxcnc-service" and e["event"] == "stop"
        )
        self.assertLess(native_end, service_end)

    def test_shared_logs_preserve_private_state_socket_and_lock(self):
        logs = self.root / "logs"
        logs.mkdir(mode=0o2750)
        logs.chmod(0o2750)
        process = self.launch(BETTERCNC_LOG_ROOT=str(logs), BETTERCNC_SHARE_LOGS="1")
        self.wait(lambda: any(path.name == "state.json" for path in logs.glob("*/state.json")))
        self.wait(
            lambda: any(
                json.loads(path.read_text())["phase"] == "ready"
                for path in logs.glob("*/state.json")
            )
        )
        run = next(logs.iterdir())
        self.assertEqual(stat.S_IMODE(run.stat().st_mode) & 0o777, 0o750)
        if sys.platform == "linux":
            self.assertTrue(run.stat().st_mode & stat.S_ISGID)
        for log in run.glob("*.log"):
            self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o640)
            self.assertEqual(log.stat().st_gid, logs.stat().st_gid)
        self.assertEqual(stat.S_IMODE((run / "state.json").stat().st_mode), 0o600)
        runtime = self.root / "run/betterlinuxcnc"
        self.assertEqual(stat.S_IMODE(runtime.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((runtime / "launcher.lock").stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((runtime / "control.sock").stat().st_mode), 0o600)
        process.terminate()
        self.assertEqual(process.wait(timeout=5), 0, self.output(process))

    def test_kiosk_native_gets_terminal_input_without_starting_a_shell(self):
        process = self.launch(BETTERCNC_KIOSK="1")
        self.ready()
        starts = [event for event in self.events() if event["event"] == "start"]
        self.assertEqual(
            [event["role"] for event in starts if event["terminal_input"]], ["linuxcnc"]
        )
        self.assertEqual(
            next(event for event in starts if event["role"] == "linuxcnc")["argv"],
            [str(self.ini.resolve())],
        )
        process.terminate()
        self.assertEqual(process.wait(timeout=5), 0, self.output(process))

    def test_busy_or_unknown_signal_preserves_native_and_controller(self):
        self.assert_preserves("running")

    def test_paused_signal_preserves_native_and_controller(self):
        self.assert_preserves("paused")

    def test_unknown_signal_preserves_native_and_controller(self):
        self.assert_preserves("unknown")

    def assert_preserves(self, state):
        (self.root / "machine.json").write_text(
            json.dumps({"programState": state, "queueDepth": 0, "activeQueueDepth": 0})
        )
        process = self.launch()
        self.ready()
        process.terminate()
        output = self.output(process)
        self.assertEqual(process.returncode, 78, output)
        self.assertIn("保留 LinuxCNC", output)
        stopped = [e["role"] for e in self.events() if e["event"] == "stop"]
        self.assertIn("betterlinuxcnc-cam-link", stopped)
        self.assertNotIn("linuxcnc", stopped)
        self.assertNotIn("betterlinuxcnc-service", stopped)

    def test_cam_failure_preserves_native_and_controller_without_restart(self):
        process = self.launch()
        self.ready()
        (self.root / "fail-cam").touch()
        output = self.output(process)
        self.assertEqual(process.returncode, 78, output)
        self.assertIn("保留 LinuxCNC", output)
        self.assertFalse(
            any(
                e["event"] == "stop" and e["role"] in ("linuxcnc", "betterlinuxcnc-service")
                for e in self.events()
            )
        )
        self.assertEqual(
            sum(e["event"] == "start" and e["role"] == "linuxcnc" for e in self.events()), 1
        )

    def test_core_readiness_timeout_never_exposes_cam_or_kills_unknown_native(self):
        self.data["startup_timeout"] = 0.5
        self.write_config()
        process = self.launch(FIXTURE_NATIVE_DELAY="30")
        output = self.output(process)
        self.assertEqual(process.returncode, 78, output)
        self.assertIn("超时", output)
        self.assertNotIn("betterlinuxcnc-cam-link", [e["role"] for e in self.events()])
        self.assertFalse(any(e["event"] == "stop" for e in self.events()))

    def test_failed_service_start_never_starts_native(self):
        process = self.launch(FIXTURE_SERVICE_FAIL="1")
        self.assertEqual(process.wait(timeout=5), 78, self.output(process))
        self.assertEqual(
            [e["role"] for e in self.events() if e["event"] == "start"], ["betterlinuxcnc-service"]
        )

    def test_second_launcher_cannot_take_over_running_stack(self):
        first = self.launch()
        self.ready()
        second = self.launch()
        self.assertIn("已在运行", self.output(second))
        self.assertEqual(second.returncode, 78)
        self.assertIsNone(first.poll())
        self.assertEqual(
            sum(e["event"] == "start" and e["role"] == "linuxcnc" for e in self.events()), 1
        )
        (self.root / "quit-native").touch()
        self.output(first)

    def test_existing_socket_is_not_deleted_or_borrowed(self):
        import socket

        path = self.root / "run/betterlinuxcnc/control.sock"
        path.parent.mkdir(parents=True, mode=0o700)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as existing:
            existing.bind(str(path))
            process = self.launch()
            self.assertIn("不会接管或删除", self.output(process))
            self.assertEqual(process.returncode, 78)
            self.assertTrue(path.exists())
            self.assertEqual(self.events(), [])

    def test_invalid_config_and_other_display_fail_before_any_child_starts(self):
        for field, value in (
            ("startup_timeout", True),
            ("startup_timeout", float("nan")),
            ("unknown", "value"),
        ):
            with self.subTest(field=field, value=value):
                self.config.write_text(json.dumps({**self.data, field: value}))
                process = self.launch("--check")
                self.output(process)
                self.assertEqual(process.returncode, 1)
        self.write_config()
        self.ini.write_text("[DISPLAY]\nDISPLAY = gmoccapy\n")
        process = self.launch()
        self.assertIn("POSTGUI_HALFILE", self.output(process))
        self.assertEqual(self.events(), [])

    def test_insecure_cam_credentials_and_missing_explicit_config_are_rejected(self):
        self.token.chmod(0o644)
        process = self.launch("--check")
        self.assertNotEqual(process.wait(timeout=5), 0, self.output(process))
        self.token.chmod(0o600)
        self.data["cam"]["host"] = "0.0.0.0"
        self.write_config()
        process = self.launch("--check")
        self.assertIn("cert/key", self.output(process))
        process = self.launch("--config", "missing.json", "--ini", str(self.ini))
        self.assertIn("启动配置不存在", self.output(process))
        self.assertEqual(self.events(), [])

    def test_installed_console_script_and_ini_only_mode(self):
        self.config.unlink()
        command = Path(sys.executable).parent / "betterlinuxcnc-launch"
        self.assertTrue(command.is_file(), "test must use the installed launcher wheel")
        result = subprocess.run(
            [str(command), "--ini", str(self.ini), "--check"],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["commands"]), 2)
        self.assertEqual(self.events(), [])

    def test_keep_alive_restarts_cam_and_controller_without_restarting_native_or_commands(self):
        process = self.launch(keep_alive=True)
        self.ready()
        for role in ("betterlinuxcnc-cam-link", "betterlinuxcnc-service"):
            starts = [e for e in self.events() if e["role"] == role and e["event"] == "start"]
            previous = starts[-1]["pid"]
            os.kill(previous, signal.SIGTERM)
            self.wait(
                lambda role=role, starts=starts: (
                    sum(e["role"] == role and e["event"] == "start" for e in self.events())
                    > len(starts)
                )
            )
            self.wait(
                lambda previous=previous: any(
                    json.loads(path.read_text()).get("phase") == "ready"
                    and previous not in json.loads(path.read_text()).get("processes", {}).values()
                    for path in self.root.glob(".runtime/launcher/*/state.json")
                )
            )
        self.assertEqual(
            sum(e["role"] == "linuxcnc" and e["event"] == "start" for e in self.events()), 1
        )
        self.assertTrue(
            all(e["method"] == "machine.status" for e in self.events() if e["event"] == "request")
        )
        process.terminate()
        self.assertEqual(process.wait(timeout=5), 0, self.output(process))

    def test_keep_alive_restarts_cleanly_exited_native_until_main_is_stopped(self):
        process = self.launch(keep_alive=True)
        self.ready()
        (self.root / "quit-native").touch()
        self.wait(lambda: any(e["event"] == "native-cleanup" for e in self.events()))
        (self.root / "quit-native").unlink()
        self.wait(
            lambda: (
                sum(e["role"] == "linuxcnc" and e["event"] == "start" for e in self.events()) >= 2
            )
        )
        process.terminate()
        output = self.output(process)
        self.assertNotIn("正在重放", output)
        self.assertIsNotNone(process.returncode)
        self.assertTrue(
            all(e["method"] == "machine.status" for e in self.events() if e["event"] == "request")
        )

    def test_session_bootstrap_imports_graphical_environment_then_starts_user_unit(self):
        command = self.bin / "systemctl"
        command.write_text(
            f"#!{sys.executable}\nimport json,sys\n"
            f"with open({str(self.root / 'systemctl-requests')!r}, 'a') as output:\n"
            "    output.write(json.dumps(sys.argv[1:])+'\\n')\n"
        )
        command.chmod(0o700)
        process = self.launch("--session-start", DISPLAY=":77", XAUTHORITY="/test/authority")
        self.assertEqual(process.wait(timeout=5), 0, self.output(process))
        requests = [
            json.loads(line) for line in (self.root / "systemctl-requests").read_text().splitlines()
        ]
        self.assertEqual(requests[0], ["--user", "daemon-reload"])
        self.assertEqual(requests[1][:2], ["--user", "import-environment"])
        self.assertIn("DISPLAY", requests[1])
        self.assertEqual(requests[2], ["--user", "start", "betterlinuxcnc-launcher.service"])
        self.assertEqual(self.events(), [])


if __name__ == "__main__":
    unittest.main()
