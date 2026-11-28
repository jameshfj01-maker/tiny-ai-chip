# SPDX-License-Identifier: Apache-2.0
#
# 데모 보드 스크립트 확인용 테스트.
#
# demoboard/tiny_ai_chip.py 는 데모 보드(RP2040/RP2350, MicroPython)에서 실제 칩을
# 시험하는 스크립트다. 칩이 오기 전에 그 스크립트가 맞는지 보려고, 같은 스크립트를
# 그대로 RTL 시뮬레이션에 연결한다.
#
#   [ tiny_ai_chip.py 의 Chip, run_all ]  <- 보드에서 돌릴 코드 그대로
#                 │ set_ui / set_uio / get_uo / get_uio / wait_clocks / reset
#        ┌────────┴─────────┐
#        v                  v
#   TTBoardAdapter      SimBoard (여기)
#   (진짜 데모 보드)     (cocotb 로 tb.v 의 핀을 움직인다)
#
# SimBoard 는 데모 보드의 "수동 클럭" (clock_project_once) 처럼 클럭을 한 번씩 직접 친다.
# 스크립트는 보통 (동기) 파이썬이라서, cocotb 의 bridge / resume 로 시뮬레이터와 잇는다.

import cocotb
from cocotb.task import bridge, resume
from cocotb.triggers import Timer

import tiny_ai_chip as script


@resume
async def _write(handle, value):
    handle.value = value
    await Timer(1, unit="ns")


@resume
async def _read(handle):
    await Timer(1, unit="ns")
    return int(handle.value)


@resume
async def _clock(dut, n):
    for _ in range(n):
        dut.clk.value = 1
        await Timer(10, unit="ns")
        dut.clk.value = 0
        await Timer(10, unit="ns")


class SimBoard:
    """데모 보드 대신 시뮬레이션 핀을 움직이는 보드 (수동 클럭 방식)."""

    exact_clocks = True  # wait_clocks(n) 이 정확히 n 클럭이다

    def __init__(self, dut):
        self.dut = dut

    def set_ui(self, value):
        _write(self.dut.ui_in, value & 0xFF)

    def set_uio(self, value):
        _write(self.dut.uio_in, value & 0xFF)

    def get_uo(self):
        return _read(self.dut.uo_out)

    def get_uio(self):
        return _read(self.dut.uio_out)

    def get_uio_oe(self):
        return _read(self.dut.uio_oe)

    def wait_clocks(self, n):
        _clock(self.dut, n)

    def reset(self):
        _write(self.dut.rst_n, 0)
        _clock(self.dut, 10)  # 동기 리셋이라 리셋 중에 클럭이 필요하다
        _write(self.dut.rst_n, 1)
        _clock(self.dut, 2)


class FaultyBoard(SimBoard):
    """일부러 고장 낸 보드: 결과 바이트를 읽을 때 맨 아래 비트를 뒤집는다.
    스크립트가 이런 고장을 정말 잡아내는지 (시험 도구를 시험) 보는 용도."""

    def get_uo(self):
        return super().get_uo() ^ 0x01


async def start(dut):
    dut.clk.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 1
    await Timer(5, unit="ns")


@cocotb.test()
async def test_script_passes_on_rtl(dut):
    """보드 스크립트의 전체 시험을 RTL 에 돌리면 전부 통과해야 한다."""
    await start(dut)
    lines = []
    summary = await bridge(script.run_all)(script.Chip(SimBoard(dut)), log=lines.append, n_random=5)
    for line in lines:
        dut._log.info(line)
    assert summary["failed"] == 0, summary
    assert summary["passed"] == summary["total"] > 0, summary


@cocotb.test()
async def test_script_detects_a_broken_chip(dut):
    """결과를 1비트만 틀리게 읽어도 스크립트가 실패를 보고해야 한다."""
    await start(dut)
    summary = await bridge(script.run_all)(script.Chip(FaultyBoard(dut)), log=lambda s: None, n_random=2)
    assert summary["failed"] > 0, summary


@cocotb.test()
async def test_compute_clocks(dut):
    """수동 클럭에서 start 부터 done 까지의 클럭 수는 576 (계산) 이상, 584 이하."""
    await start(dut)

    def measure():
        chip = script.Chip(SimBoard(dut))
        chip.board.reset()
        chip.load([[1, 2], [3, 4]], [[5, 6], [7, 8]])
        clocks = chip.run()
        return clocks, chip.read_c()

    clocks, C = await bridge(measure)()
    dut._log.info(f"start -> done: {clocks} clocks")
    assert 576 <= clocks <= 584
    assert C == [[19, 22], [43, 50]]


@cocotb.test()
async def test_script_4x4(dut):
    """스크립트의 4x4 행렬곱 (2x2 블록 + 더하기 모드) 이 RTL 에서 맞게 나온다. 끝값 65536 포함."""
    await start(dut)

    def run():
        chip = script.Chip(SimBoard(dut))
        chip.board.reset()
        A = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16]]
        B = [[1, 0, 0, 1], [0, 1, 1, 0], [-1, 0, 2, 0], [0, -2, 0, 3]]
        M = [[-128] * 4 for _ in range(4)]
        return chip.matmul4(A, B), script.matmul_ref(A, B), chip.matmul4(M, M)

    got, want, worst = await bridge(run)()
    assert got == want
    assert worst == [[65536] * 4 for _ in range(4)]


@cocotb.test()
async def test_reference_model_matches_examples(dut):
    """스크립트 안의 정답 계산(파이썬 행렬곱)과 무작위 값 생성기를 확인한다."""
    assert script.matmul_ref([[1, 2], [3, 4]], [[5, 6], [7, 8]]) == [[19, 22], [43, 50]]
    I4 = [[1 if i == j else 0 for j in range(4)] for i in range(4)]
    A4 = [[i * 4 + j - 8 for j in range(4)] for i in range(4)]
    assert script.matmul_ref(A4, I4) == A4
    rng = script.Lcg(2026)
    values = [rng.int8() for _ in range(1000)]
    assert min(values) >= -128 and max(values) <= 127
    assert min(values) < -100 and max(values) > 100  # 범위를 고루 쓴다
    assert script.Lcg(2026).int8() == script.Lcg(2026).int8()  # 같은 씨앗이면 같은 값
