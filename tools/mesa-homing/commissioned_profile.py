"""Stage the unchanged paired module for the fixed commissioned machine profile."""

REVISION = "zhulong-xyz-v5-20261026"


def prepare_profile(module_work, vendor):
    # Direction and staged retreat logic belong to the upstream HOMEMOD.
    # Keep an explicit copy for the public harness and checksum provenance.
    (module_work / "homing.c").write_bytes((vendor / "homing/src/homing.c").read_bytes())
