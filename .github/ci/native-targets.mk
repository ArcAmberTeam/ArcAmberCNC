# CI-only targets, included AFTER src/Makefile. Reuse the native dependency graph.
# Dependencies can cross these build scopes; each requested output has one owner.
.PHONY: ci-hal ci-motion ci-drivers ci-task ci-interpreter ci-python-extensions
ci-hal: ../lib/liblinuxcnchal.so ../rtlib/hal_lib.so ../bin/halcmd
ci-motion: ../rtlib/motmod.so ../rtlib/tpmod.so ../rtlib/homemod.so ../rtlib/pid.so

# Select every driver module enabled by this platform's native Makefile.
CI_DRIVER_MODULES := $(foreach module,$(obj-m),$(if $(filter hal/drivers/%,$($(module:.o=)-objs)),$(module)))
ifeq ($(strip $(CI_DRIVER_MODULES)),)
$(error No native driver modules selected)
endif
# Include the relocated C and C++ userspace device capabilities when enabled.
CI_USER_DRIVER_NAMES := mb2hal hy_vfd gs2_vfd hy_gt_vfd svd-ps_vfd \
    vfs11_vfd vfdb_vfd wj200_vfd pi500_vfd shuttle xhc-hb04 xhc-whb04b-6
CI_USER_DRIVERS := $(filter $(addprefix ../bin/,$(CI_USER_DRIVER_NAMES)),$(TARGETS))
ci-drivers: $(patsubst %.o,../rtlib/%.so,$(CI_DRIVER_MODULES)) ../rtlib/stepgen.so ../rtlib/encoder.so $(CI_USER_DRIVERS)
ci-task: ../bin/milltask ../bin/linuxcncsvr
ci-interpreter: ../bin/rs274 ../lib/librs274.so
ci-python-extensions: ../lib/python/linuxcnc.so ../lib/python/gcode.so ../lib/python/_hal.so
