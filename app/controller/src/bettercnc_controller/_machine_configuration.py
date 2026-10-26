"""Read active axis configuration without command or error-channel access."""

import math

AXES = "XYZABCUVW"


def machine_configuration(module, status):
    """Return canonical mm/degree limits from the running machine's INI.

    Axis presence comes from NML, never JOINTS or unused INI sections. An axis
    list does not certify simultaneous machining or a rotary pivot geometry.
    Configuration failure must not hide otherwise valid execution feedback.
    """
    try:
        path = getattr(status, "ini_filename", None)
        if not path:
            return None
        ini = module.ini(path)
        mask = int(status.axis_mask)
        if mask <= 0 or mask & ~0x1FF:
            return None

        def number(section, key, factor):
            value = ini.find(section, key)
            if value is None:
                return None
            try:
                value = float(value) / factor
            except (TypeError, ValueError, OverflowError):
                return None
            return value if math.isfinite(value) else None

        axes = []
        for index, name in enumerate(AXES):
            if not mask & (1 << index):
                continue
            rotary = name in "ABC"
            factor = float(status.angular_units if rotary else status.linear_units)
            if not math.isfinite(factor) or factor <= 0:
                return None
            section = "AXIS_" + name
            minimum = number(section, "MIN_LIMIT", factor)
            maximum = number(section, "MAX_LIMIT", factor)
            if (
                minimum is not None
                and maximum is not None
                and (minimum >= maximum or not math.isfinite(maximum - minimum))
            ):
                minimum = maximum = None
            velocity = number(section, "MAX_VELOCITY", factor / 60)
            axes.append(
                {
                    "name": name,
                    "kind": "rotary" if rotary else "linear",
                    "unit": "deg" if rotary else "mm",
                    "min": minimum,
                    "max": maximum,
                    "maxVelocity": velocity if velocity is not None and velocity > 0 else None,
                }
            )
        kinematics = ini.find("KINS", "KINEMATICS")
        return {
            "schemaVersion": 1,
            "axes": axes,
            "kinematics": str(kinematics)[:256] if kinematics else None,
        }
    except Exception:
        return None
