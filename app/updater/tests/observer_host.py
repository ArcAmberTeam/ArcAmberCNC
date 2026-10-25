"""Real public observer service with a test-owned LinuxCNC vendor interface."""

import asyncio
import signal
import sys
from pathlib import Path

from bettercnc_controller import StatusReader
from betterlinuxcnc_service import serve
from test_controller import FakeLinuxCNC


def forbidden(*_args, **_kwargs):
    raise AssertionError("updater must not create commands or consume errors")


async def main():
    module = FakeLinuxCNC()
    module.command = module.error_channel = forbidden
    module.status.task_state = module.STATE_OFF
    module.status.enabled = False
    scenario = sys.argv[2]
    if scenario == "busy":
        module.status.interp_state = module.INTERP_READING
    elif scenario == "native-pending":
        module.status.state = module.RCS_EXEC
    elif scenario == "unknown-velocity":
        module.status.current_vel = float("nan")
    elif scenario == "powered":
        module.status.task_state = module.STATE_ON
        module.status.enabled = True
    stop = asyncio.Event()
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, stop.set)
    await serve(
        Path(sys.argv[1]),
        controller_factory=forbidden,
        status_reader_factory=lambda **kwargs: StatusReader(module=module, **kwargs),
        stop_event=stop,
    )


asyncio.run(main())
