# LinuxCNC Python interface

Owns the compiled `linuxcnc` Python module, previously housed in AXIS.
The public interface remains `import linuxcnc`: command, stat, error_channel,
ini, positionlogger and existing constants. Callers must not depend on this
source layout. This module neither launches nor depends on an AXIS display.

The upstream extension includes the OpenGL positionlogger used by existing
previews; its API and epoxy link dependency are intentionally preserved.
Standalone commands belong to `../python-tools/`; Tk/OpenGL widget support
belongs to `../tk-support/`. Neither is a build dependency of this module.
