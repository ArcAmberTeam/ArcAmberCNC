"""Read machining feedback without opening command or error channels."""

import importlib
import os


class StatusReader:
    """Poll fresh NML status on the service worker, independently of UI ownership.

    Line numbers describe observed execution, not a time or completion percentage.
    This reader never consumes the shared error channel or creates commands.
    """

    def __init__(self, ini_path=None, module=None):
        self._ini = ini_path
        self._module = module
        self._stat = None

    def poll(self):
        try:
            if self._module is None:
                self._module = importlib.import_module("linuxcnc")
            module = self._module
            if self._stat is None:
                self._stat = module.stat()
            s = self._stat
            s.poll()
            actual_ini = getattr(s, "ini_filename", None)
            if self._ini and (
                not actual_ini or os.path.realpath(self._ini) != os.path.realpath(actual_ini)
            ):
                raise ValueError("running LinuxCNC INI does not match the service")
            modes = {module.MODE_MANUAL: "manual", module.MODE_MDI: "mdi", module.MODE_AUTO: "auto"}
            states = (
                module.STATE_ESTOP,
                module.STATE_ESTOP_RESET,
                module.STATE_OFF,
                module.STATE_ON,
            )
            if (
                s.task_mode not in modes
                or s.task_state not in states
                or s.joints <= 0
                or s.axis_mask <= 0
                or s.linear_units <= 0
            ):
                raise ValueError("LinuxCNC status is not initialized")
            busy = (
                s.interp_state != module.INTERP_IDLE
                or not s.inpos
                or s.exec_state != module.EXEC_DONE
                or s.queue > 0
                or s.active_queue > 0
            )
            state = "idle"
            if s.task_mode == module.MODE_AUTO:
                state = "paused" if s.paused else "running" if busy else "idle"
            elif busy:
                state = "busy"
            estop = bool(s.estop) or s.task_state == module.STATE_ESTOP
            powered = s.task_state == module.STATE_ON and bool(s.enabled)
            if estop:
                state = "estop"
            elif not powered:
                state = "off"
            return {
                "connected": True,
                "programState": state,
                "file": str(s.file),
                "mode": modes[s.task_mode],
                "powered": powered,
                "estop": estop,
                "paused": bool(s.paused),
                "currentLine": int(s.motion_line),
                "taskLine": int(s.current_line),
                "readLine": int(getattr(s, "read_line", 0)),
                "progressPercent": None,
                "queueDepth": int(s.queue),
                "activeQueueDepth": int(s.active_queue),
                "tool": int(s.tool_in_spindle),
                "spindleSpeed": float(s.spindle[0]["speed"]),
                "feedOverride": float(s.feedrate),
                "flood": bool(s.flood),
                "mist": bool(s.mist),
            }
        except Exception:
            self._stat = None
            return {
                "connected": False,
                "programState": "unknown",
                "file": None,
                "currentLine": None,
                "taskLine": None,
                "readLine": None,
                "progressPercent": None,
            }

    def close(self):
        self._stat = None
