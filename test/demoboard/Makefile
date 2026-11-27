# 데모 보드 스크립트 (demoboard/tiny_ai_chip.py) 를 실제 칩 대신 RTL 시뮬레이션에 연결해서 확인한다.

SIM ?= icarus
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES += $(SRC_DIR)/project.v $(SRC_DIR)/systolic_2x2.v $(SRC_DIR)/mac_serial.v
VERILOG_SOURCES += $(PWD)/../tb.v
COCOTB_TOPLEVEL = tb
COCOTB_TEST_MODULES = test_demoboard_script

# 데모 보드 스크립트를 import 할 수 있게 한다.
export PYTHONPATH := $(PWD)/../../demoboard:$(PYTHONPATH)

include $(shell cocotb-config --makefiles)/Makefile.sim
