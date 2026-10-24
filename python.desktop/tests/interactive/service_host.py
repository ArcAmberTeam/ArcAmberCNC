"""Host the unchanged public control service with test-owned external adapters."""
import asyncio
import json
import tempfile
import threading
import time
from pathlib import Path

from bettercnc_controller import Controller, StatusReader
from betterlinuxcnc_service import serve

from .linear_program import read_linear_program
from .vendor import LinuxCNCInterface


def write_configuration(folder):
    folder = Path(folder)
    ini = folder / "interface-test.ini"
    ini.write_text("""[KINS]
JOINTS = 3
KINEMATICS = trivkins coordinates=XYZ
[TRAJ]
MAX_LINEAR_VELOCITY = 20
[DISPLAY]
MAX_LINEAR_VELOCITY = 20
MAX_FEED_OVERRIDE = 1.5
MIN_SPINDLE_OVERRIDE = 0.5
MAX_SPINDLE_OVERRIDE = 1.5
DEFAULT_SPINDLE_SPEED = 6000
MIN_SPINDLE_SPEED = 0
MAX_SPINDLE_SPEED = 24000
PROGRAM_PREFIX = .
[RS274NGC]
PARAMETER_FILE = machine.var
[EMCIO]
TOOL_TABLE = tool.tbl
""" + "".join(f"""[AXIS_{axis}]
MIN_LIMIT = -100
MAX_LIMIT = 200
MAX_VELOCITY = 20
[JOINT_{i}]
MAX_VELOCITY = 20
HOME_SEQUENCE = {i}
""" for i, axis in enumerate("XYZ")), encoding="utf-8")
    (folder / "machine.var").write_text("", encoding="utf-8")
    (folder / "tool.tbl").write_text("T1 P1 Z0 D6 ; test tool\n", encoding="utf-8")
    return ini


class PreviewProcess:
    """Implement only the process-factory contract; never launch an interpreter."""
    def __init__(self, args):
        request = json.loads(Path(args[args.index("--request") + 1]).read_text())
        output = Path(args[args.index("--output") + 1])
        try:
            data = read_linear_program(request["path"])
            result = {key: data[key] for key in ("segments", "bounds")}
            result.update(units="mm", truncated=False,
                          warnings=["外部接口替身：仅 G0/G1 测试几何，非 LinuxCNC 解释器结果"])
        except (OSError, ValueError) as error:
            result = dict(segments=[], bounds={"min": [], "max": []}, units="mm",
                          error={"message": str(error), "line": 0}, warnings=[], truncated=False)
        output.write_text(json.dumps(result), encoding="utf-8")
        self.returncode = 0

    async def wait(self):
        return self.returncode

    def terminate(self):
        pass

    def kill(self):
        pass


async def preview_process(*args, **kwargs):
    return PreviewProcess(args)


class ServiceHost:
    def __init__(self):
        # Short /tmp path fits macOS sockaddr_un; private 0700 test directory.
        self.directory = tempfile.TemporaryDirectory(prefix="cnc-api-", dir="/tmp")
        self.folder = Path(self.directory.name).resolve()
        self.ini = write_configuration(self.folder)
        self.socket = self.folder / "control.sock"
        self.vendor = LinuxCNCInterface(self.ini)
        self.loop, self.stopped, self.failure = None, None, None
        self.thread = threading.Thread(target=self._run, name="Test control service")

    def start(self):
        self.thread.start()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.failure:
                self.close()
                raise RuntimeError("Test service failed") from self.failure
            if self.socket.exists():
                return self
            time.sleep(0.01)
        self.close()
        raise TimeoutError("Test control service did not start")

    def _run(self):
        async def run():
            self.loop = asyncio.get_running_loop()
            self.stopped = asyncio.Event()
            await serve(self.socket, ini_path=str(self.ini),
                        controller_factory=lambda **kwargs: Controller(module=self.vendor, **kwargs),
                        status_reader_factory=lambda **kwargs: StatusReader(module=self.vendor, **kwargs),
                        process_factory=preview_process, stop_event=self.stopped)
        try:
            asyncio.run(run())
        except Exception as error:
            self.failure = error

    def close(self):
        if self.loop and self.stopped and self.thread.is_alive():
            self.loop.call_soon_threadsafe(self.stopped.set)
        if self.thread.ident:
            self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise RuntimeError("Test service did not stop")
        self.directory.cleanup()
