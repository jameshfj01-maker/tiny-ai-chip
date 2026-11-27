# 비트 직렬 MAC 유닛 단독 테스트용 Makefile.

SIM ?= icarus
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES += $(SRC_DIR)/mac_serial.v
COCOTB_TOPLEVEL = mac_serial
COCOTB_TEST_MODULES = test_mac_serial

include $(shell cocotb-config --makefiles)/Makefile.sim
