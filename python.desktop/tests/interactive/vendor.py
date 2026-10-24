"""Test-only LinuxCNC Python API double; never loads linuxcnc, HAL or drivers.

Only the controller worker accesses vendor state. The console sends queued
inputs and reads locked diagnostic copies. Motion is bounded linear playback,
not LinuxCNC trajectory planning or a physical machine model.
"""
import configparser
import math
import time
from collections import deque
from copy import deepcopy
from queue import Empty, SimpleQueue
from threading import Lock
from types import SimpleNamespace

from .linear_program import INITIAL, read_linear_program


class LinuxCNCInterface:
    MODE_MANUAL, MODE_MDI, MODE_AUTO = 1, 2, 3
    STATE_ESTOP, STATE_ESTOP_RESET, STATE_OFF, STATE_ON = 1, 2, 3, 4
    TRAJ_MODE_FREE, TRAJ_MODE_COORD, TRAJ_MODE_TELEOP = 1, 2, 3
    INTERP_IDLE, INTERP_READING, INTERP_PAUSED = 1, 2, 3
    EXEC_DONE = 1
    RCS_DONE, RCS_EXEC, RCS_ERROR = 1, 2, 3
    NML_ERROR, OPERATOR_ERROR, OPERATOR_TEXT = 1, 2, 3
    JOG_STOP, JOG_CONTINUOUS, JOG_INCREMENT = 0, 1, 2
    AUTO_RUN, AUTO_STEP, AUTO_PAUSE, AUTO_RESUME = 0, 1, 2, 3
    SPINDLE_FORWARD, SPINDLE_REVERSE, SPINDLE_OFF = 1, -1, 0
    SPINDLE_INCREASE, SPINDLE_DECREASE = 10, 11
    BRAKE_ENGAGE, BRAKE_RELEASE = 1, 0
    FLOOD_ON, FLOOD_OFF, MIST_ON, MIST_OFF = 1, 0, 1, 0

    def __init__(self, ini_path, *, clock=time.monotonic):
        self.clock, self.last_time = clock, clock()
        self.inputs, self.lock = SimpleQueue(), Lock()
        self.events, self.errors, self.pending = deque(maxlen=500), deque(), deque()
        self.available, self.rate, self.ack_delay = True, 1.0, 0.12
        self.data, self.index, self.elapsed = None, 0, 0.0
        self.running, self.single_step = False, False
        self.home_move, self.jogs = None, {}
        self.status_text = "急停中 · 先解除急停、上电、回零"
        self.status = SimpleNamespace(
            task_state=self.STATE_ESTOP, debug=0, task_mode=self.MODE_MANUAL,
            enabled=False, estop=True, joints=3, axis_mask=7, homed=[0, 0, 0],
            joint=[dict(homing=False, override_limits=False, min_hard_limit=False,
                        max_hard_limit=False) for _ in range(3)],
            motion_mode=self.TRAJ_MODE_FREE, interp_state=self.INTERP_IDLE,
            exec_state=self.EXEC_DONE, inpos=True, queue=0, active_queue=0,
            echo_serial_number=0, state=self.RCS_DONE,
            actual_position=INITIAL[:] + [0.0] * 6, position=INITIAL[:] + [0.0] * 6,
            g5x_offset=[0.0]*9, g92_offset=[0.0]*9, tool_offset=[0.0]*9, dtg=[0.0]*9,
            rotation_xy=0.0, linear_units=1.0, angular_units=1.0,
            current_vel=0.0, max_velocity=20.0, feedrate=1.0, rapidrate=1.0,
            spindle=[dict(override=1.0, speed=0.0, direction=0, brake=False)],
            flood=False, mist=False, optional_stop=False, block_delete=False,
            file="", motion_line=0, current_line=0, tool_in_spindle=1,
            gcodes=[0, 170, 210, 400, 490, 540, 800, 900, 940, -1],
            mcodes=[0, 5, 9, -1], g5x_index=1, tool_table=[], paused=False,
            ini_filename=str(ini_path), poll=self._poll,
        )
        self.commands = Commands(self)
        self._publish()

    def stat(self):
        return self.status

    def command(self):
        return self.commands

    def error_channel(self):
        return SimpleNamespace(poll=lambda: self.errors.popleft() if self.errors else None)

    def ini(self, path):
        parser = configparser.ConfigParser(interpolation=None)
        if not parser.read(path):
            raise ValueError("测试 INI 不存在")
        return SimpleNamespace(find=lambda section, key: parser.get(section, key, fallback=None))

    def inject(self, name, value=None):
        """Thread-safe test controls, separate from the vendor command channel."""
        if name not in {"rate", "connection", "estop", "error", "delay"}:
            raise ValueError("Unknown test input")
        self.inputs.put((name, value))

    def diagnostics(self):
        with self.lock:
            return deepcopy(self.report)

    def _event(self, kind, **values):
        self.events.append(dict(time=round(self.clock(), 6), kind=kind, **values))

    def _publish(self):
        s = self.status
        with self.lock:
            self.report = dict(
                status=self.status_text, available=self.available, rate=self.rate,
                progress=self.index / len(self.data["blocks"]) if self.data else 0,
                actualPosition=s.actual_position[:], currentLine=s.motion_line,
                serial=self.commands.serial, echo=s.echo_serial_number,
                events=list(self.events),
            )

    def _halt(self, message):
        s = self.status
        self.running, self.home_move = False, None
        self.jogs.clear()
        s.interp_state, s.paused, s.inpos = self.INTERP_IDLE, False, True
        s.position, s.dtg, s.current_vel = s.actual_position[:], [0.0]*9, 0.0
        s.spindle[0].update(speed=0.0, direction=0)
        for joint in s.joint:
            joint["homing"] = False
        self.status_text = message

    def _poll(self):
        now = self.clock()
        dt = max(0.0, now - self.last_time)
        self.last_time = now
        # Advance existing motion before applying newly received inputs.
        self._move(dt * self.rate)
        while True:
            try:
                name, value = self.inputs.get_nowait()
            except Empty:
                break
            self._event("injection", name=name, value=value)
            if name == "rate":
                self.rate = max(0.1, min(10.0, float(value)))
            elif name == "delay":
                self.ack_delay = max(0.0, min(10.0, float(value)))
            elif name == "connection":
                self.available = bool(value)
            elif name == "estop":
                self._apply("state", (self.STATE_ESTOP,))
            elif name == "error":
                self.errors.append((self.OPERATOR_ERROR, "测试注入：伺服驱动报警"))
                self._halt("驱动报警 · 运动已停止")
        while self.pending and self.pending[0][0] <= now:
            _, serial, method, args = self.pending.popleft()
            try:
                self._apply(method, args)
                self.status.state = self.RCS_DONE
                self._event("ack", serial=serial, method=method)
            except (ValueError, OSError) as error:
                self.status.state = self.RCS_ERROR
                self.errors.append((self.OPERATOR_ERROR, str(error)))
                self._event("rejected", serial=serial, message=str(error))
            self.status.echo_serial_number = serial
        self._publish()
        if not self.available:
            raise RuntimeError("测试注入：NML 状态通道断开")

    def _apply(self, method, args):
        s = self.status
        if method == "state":
            target = args[0]
            if target == self.STATE_ON and s.estop:
                raise ValueError("模拟外部接口拒绝：急停未解除")
            s.task_state, s.enabled, s.estop = target, target == self.STATE_ON, target == self.STATE_ESTOP
            if not s.enabled:
                self._halt("急停中" if s.estop else "电源关闭")
            else:
                self.status_text = "电源开启"
        elif method == "mode":
            s.task_mode = args[0]
        elif method == "teleop_enable":
            s.motion_mode = self.TRAJ_MODE_TELEOP if args[0] else self.TRAJ_MODE_FREE
        elif method in {"home", "unhome"}:
            if not s.enabled or s.estop:
                raise ValueError("模拟外部接口拒绝：未上电")
            indices = list(range(3)) if args[0] == -1 else [args[0]]
            for i in indices:
                s.homed[i] = 0
                s.joint[i]["homing"] = method == "home"
            if method == "home":
                # Test datum is X0 Y0 Z5; no switch/servo physics are implied.
                self.home_move = [indices, s.actual_position[:], 0.0]
                s.inpos = False
                self.status_text = "回零中"
        elif method == "program_open":
            self.data = read_linear_program(args[0])
            s.file, self.index, self.elapsed = self.data["path"], 0, 0.0
            self.status_text = "程序已加载"
        elif method == "auto":
            if not s.enabled or s.estop or not all(s.homed):
                raise ValueError("模拟外部接口拒绝：未上电或未回零")
            if args[0] == self.AUTO_PAUSE:
                s.paused, s.interp_state, s.current_vel = True, self.INTERP_PAUSED, 0.0
                self.status_text = "已暂停"
            elif args[0] == self.AUTO_RESUME:
                s.paused, s.interp_state = False, self.INTERP_READING
                self.single_step = False
                self.status_text = "运行中"
            else:
                if not self.data:
                    raise ValueError("尚未打开程序")
                if not self.running:
                    if args[0] == self.AUTO_RUN and len(args) > 1 and args[1] != 0:
                        raise ValueError("测试接口不支持从指定行启动")
                    self.index, self.elapsed = 0, 0.0
                self.running = True
                self.single_step = args[0] == self.AUTO_STEP
                s.paused, s.interp_state, s.inpos = False, self.INTERP_READING, False
                self.status_text = "运行中"
        elif method == "abort":
            self._halt("已停止")
        elif method == "jog":
            command, _, index, *values = args
            if command == self.JOG_STOP:
                self.jogs.pop(index, None)
                s.current_vel = 0.0
            else:
                if not s.enabled or s.estop:
                    raise ValueError("模拟外部接口拒绝：未上电")
                velocity = values[0]
                remaining = values[1] if command == self.JOG_INCREMENT else math.inf
                self.jogs[index] = [velocity, remaining]
        elif method in {"feedrate", "rapidrate", "debug"}:
            setattr(s, method, args[0])
        elif method == "maxvel":
            s.max_velocity = args[0]
        elif method in {"flood", "mist"}:
            setattr(s, method, bool(args[0]))
        elif method in {"set_optional_stop", "set_block_delete"}:
            setattr(s, method.removeprefix("set_"), bool(args[0]))
        elif method == "spindleoverride":
            s.spindle[0]["override"] = args[0]
        elif method == "spindle" and args[0] in {-1, 0, 1}:
            s.spindle[0].update(direction=args[0], speed=args[0] * (args[1] if len(args) > 1 else 0))
        elif method == "brake":
            s.spindle[0]["brake"] = bool(args[0])
        else:
            raise ValueError(f"测试接口未实现 {method}，未执行")

    def _move(self, dt):
        s = self.status
        if self.home_move:
            indices, start, elapsed = self.home_move
            elapsed = min(1.0, elapsed + dt)
            self.home_move[2] = elapsed
            for i in indices:
                s.actual_position[i] = start[i] + (INITIAL[i] - start[i]) * elapsed
            s.position = s.actual_position[:]
            if elapsed == 1:
                for i in indices:
                    s.homed[i], s.joint[i]["homing"] = 1, False
                self.home_move, s.inpos, self.status_text = None, True, "回零完成"
                self._event("homed", joints=indices)
        for i, (velocity, remaining) in list(self.jogs.items()):
            distance = min(abs(velocity) * dt, remaining)
            s.actual_position[i] += math.copysign(distance, velocity)
            s.position = s.actual_position[:]
            s.current_vel = abs(velocity)
            self.jogs[i][1] -= distance
            if self.jogs[i][1] <= 1e-9:
                del self.jogs[i]
                s.current_vel = 0.0
        if not self.running or s.paused:
            return
        while dt > 0 and self.index < len(self.data["blocks"]):
            block = self.data["blocks"][self.index]
            if self.elapsed == 0:
                self.block_start = s.actual_position[:3]
                # Preserve unspecified axes when restarting at a stopped pose.
                self.block_end = self.block_start[:]
                for axis, value in block["axes"].items():
                    self.block_end[axis] = value
                distance = math.dist(self.block_start, self.block_end)
                self.block_duration = max(0.15, distance / block["velocity"]) if block["velocity"] else 0.15
            factor = (s.rapidrate if block["rapid"] else s.feedrate) if block["motion"] else 1.0
            if block["velocity"]:
                factor = min(factor, s.max_velocity / block["velocity"])
            if factor <= 0:
                s.current_vel = 0.0
                break
            spent = min(dt, (self.block_duration - self.elapsed) / factor)
            self.elapsed += spent * factor
            dt -= spent
            fraction = min(1.0, self.elapsed / self.block_duration)
            s.actual_position[:3] = [a + (b-a)*fraction for a, b in zip(self.block_start, self.block_end)]
            s.position[:3] = self.block_end
            s.dtg[:3] = [b-a for a, b in zip(s.actual_position[:3], self.block_end)]
            s.motion_line = block["line"]
            s.current_vel = block["velocity"] * factor
            s.spindle[0].update(speed=block["spindle"], direction=int(block["spindle"] > 0))
            if fraction < 1:
                break
            self.index, self.elapsed = self.index + 1, 0.0
            if self.index == len(self.data["blocks"]):
                self._halt("已完成")
                self._event("program-complete", position=s.actual_position[:3])
            elif self.single_step:
                s.paused, s.interp_state, s.current_vel = True, self.INTERP_PAUSED, 0.0
                self.status_text = "单段结束"
                break


class Commands:
    METHODS = {"mode", "state", "teleop_enable", "home", "unhome", "auto", "abort",
               "program_open", "set_optional_stop", "set_block_delete", "debug", "flood",
               "mist", "feedrate", "rapidrate", "maxvel", "spindleoverride", "spindle",
               "brake", "jog", "mdi", "override_limits", "load_tool_table"}

    def __init__(self, vendor):
        self.vendor, self.serial = vendor, 0

    def __getattr__(self, method):
        if method not in self.METHODS:
            raise AttributeError(method)

        def send(*args):
            v = self.vendor
            if not v.available:
                raise RuntimeError("模拟命令通道断开")
            self.serial += 1
            v.pending.append((v.clock() + v.ack_delay, self.serial, method, args))
            v._event("command", serial=self.serial, method=method, args=list(args))
        return send
