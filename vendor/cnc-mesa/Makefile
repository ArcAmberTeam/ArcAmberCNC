PYTHON ?= python3
export PYTHONPATH := $(CURDIR)/mesa

.PHONY: check test-hdl test-homing prepare-firmware prepare-homing prepare-linuxcnc inspect-firmware
check:
	$(PYTHON) tools/check_workspace.py
	$(PYTHON) -m unittest discover -s tests -v

prepare-firmware:
	$(PYTHON) firmware/prepare.py

prepare-homing:
	$(PYTHON) homing/prepare.py

prepare-linuxcnc:
	$(PYTHON) linuxcnc/prepare.py

inspect-firmware:
	$(PYTHON) tools/inspect_firmware.py mesa/firmware/original/TopEthernetHostMot2.bit

test-hdl:
	$(PYTHON) tools/test_hdl.py

test-homing: prepare-homing
	$(PYTHON) tools/test_homing.py
