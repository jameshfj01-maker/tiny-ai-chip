# MAC 유닛 단독 테스트용 Makefile.
# 최상위 모듈(test/Makefile)과 따로, mac 모듈 하나만 시뮬레이션한다.

SIM ?= icarus
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES += $(SRC_DIR)/mac.v
COCOTB_TOPLEVEL = mac
COCOTB_TEST_MODULES = test_mac

include $(shell cocotb-config --makefiles)/Makefile.sim
