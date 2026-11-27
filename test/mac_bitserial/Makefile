# 완전 비트 직렬 MAC (+ 순서 지휘자) 단독 테스트용 Makefile.

SIM ?= icarus
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES += $(SRC_DIR)/bitserial_seq.v $(SRC_DIR)/mac_bitserial.v $(PWD)/tb_mac_bitserial.v
COCOTB_TOPLEVEL = tb_mac_bitserial
COCOTB_TEST_MODULES = test_mac_bitserial

include $(shell cocotb-config --makefiles)/Makefile.sim
