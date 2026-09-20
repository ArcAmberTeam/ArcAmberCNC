#!/usr/bin/env python3
"""Headless simulation acceptance: reset, home XYZ, execute MDI, verify motion."""
import json
import time
from pathlib import Path

import linuxcnc


def main():
    command = linuxcnc.command()
    status = linuxcnc.stat()
    errors = linuxcnc.error_channel()

    def check_errors():
        while (error := errors.poll()) is not None:
            if error[0] in (linuxcnc.NML_ERROR, linuxcnc.OPERATOR_ERROR):
                raise RuntimeError(error[1])

    def wait_for(predicate, description, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status.poll()
            check_errors()
            if predicate():
                return
            time.sleep(0.05)
        raise TimeoutError(description)

    def completed():
        if command.wait_complete(30) != linuxcnc.RCS_DONE:
            raise RuntimeError("LinuxCNC command did not complete")
        check_errors()

    command.state(linuxcnc.STATE_ESTOP_RESET)
    completed()
    command.state(linuxcnc.STATE_ON)
    completed()
    command.mode(linuxcnc.MODE_MANUAL)
    completed()
    for joint in range(3):
        command.home(joint)
        completed()
    wait_for(lambda: all(status.homed[:3]), "XYZ homing")
    command.mode(linuxcnc.MODE_MDI)
    completed()
    for line in ("G20 G90 G54 G40 G49 G80", "G1 X1 Y2 Z3 F600", "G1 X0 Y0 Z0 F600"):
        command.mdi(line)
        completed()
        target = (1, 2, 3) if "X1" in line else (0, 0, 0)
        if line.startswith("G1"):
            wait_for(lambda: all(abs(status.actual_position[i] - target[i]) < 0.001
                                 for i in range(3)) and status.inpos,
                     f"motion to {target}")
    command.state(linuxcnc.STATE_OFF)
    completed()
    Path("smoke-success.json").write_text(json.dumps({
        "homed": True, "mdi_motion": True, "returned_to_origin": True,
    }) + "\n")
    print("STAGING_SMOKE_OK", flush=True)


if __name__ == "__main__":
    main()
