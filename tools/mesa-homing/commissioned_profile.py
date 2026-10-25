"""Adapt the pinned reference module to the operator-confirmed axis directions.

The vendor snapshot remains byte-identical to its paired release. The installed
module records this adapter's hash and exercises both signed profiles in CI.
"""

from pathlib import Path

REVISION = "zhulong-xyz-20261026"
REPLACEMENTS = (
    (
        "joint_num == 1 ? joint->on_neg_limit : joint->on_pos_limit",
        "H[joint_num].home_offset > 0.0 ? joint->on_neg_limit : joint->on_pos_limit",
    ),
    (
        "double direction = joint_num == 1 ? 1.0 : -1.0;",
        "double direction = H[joint_num].home_offset > 0.0 ? 1.0 : -1.0;",
    ),
)


def prepare_profile(module_work, vendor, work):
    source = module_work / "homing.c"
    content = (vendor / "homing/src/homing.c").read_text()
    for before, after in REPLACEMENTS:
        if content.count(before) != 1:
            raise ValueError(
                "Pinned HOMEMOD changed; review the signed-profile adapter"
            )
        content = content.replace(before, after)
    source.write_text(content)
    template = (vendor / "homing/zhulong_homing.comp").read_text()
    (module_work / "zhulong_homing.comp").write_text(
        template.replace('#include "homing.c"', content)
    )
    harness = (vendor / "tests/homing/test_homing.c").read_text()
    if harness.count("axis == 1 ? 1 : -1") != 1 or harness.count("if (axis == 1)") != 2:
        raise ValueError(
            "Pinned HOMEMOD harness changed; review the axis-direction cases"
        )
    harness = harness.replace("axis == 1 ? 1 : -1", "-1")
    harness = harness.replace("if (axis == 1)", "if (direction > 0)")
    target = Path(work) / "test_commissioned_homing.c"
    target.write_text(harness)
    return target
