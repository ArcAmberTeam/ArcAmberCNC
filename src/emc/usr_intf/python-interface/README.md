# LinuxCNC Python interface

[Project module map](../../../../docs/module-map.md) · [Execution coordinator](../../task/README.md)

## Role and language

`emcmodule.cc` is a compiled C++ extension exposed through `import linuxcnc`. It provides `command`, `stat`, `error_channel`, `ini`, `positionlogger`, and existing constants. Python is the calling language; C++ implements the channels and extension.

UIs or a future Python controller service submit actions to Task through NML commands, obtain snapshots through the status channel, and consume messages through the error channel. Callers should not depend on this directory's layout. Our `backend/` does not currently import this module and is not yet connected to the machine.

## Responsibility boundaries

This module originally lived in AXIS and is now retained separately; it neither starts nor depends on the AXIS UI. It provides LinuxCNC access without owning the new service's control ownership/session rules or running a real-time servo loop.

The upstream OpenGL `positionlogger` remains available to existing previews; retain its API and epoxy link dependency. Independent commands belong in `../python-tools/`, and Tk/OpenGL widget support in `../tk-support/`; neither is a build dependency of this module.

Extension changes require native-build and Python import/API compatibility checks. Socket tests for the new service cannot replace extension verification.
