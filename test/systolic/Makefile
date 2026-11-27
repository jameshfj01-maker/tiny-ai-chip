# 2x2 systolic array 단독 테스트용 Makefile.

SIM ?= icarus
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES += $(SRC_DIR)/bitserial_seq.v $(SRC_DIR)/mac_bitserial.v $(SRC_DIR)/systolic_2x2.v
COCOTB_TOPLEVEL = systolic_2x2
COCOTB_TEST_MODULES = test_systolic

include $(shell cocotb-config --makefiles)/Makefile.sim
