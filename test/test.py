# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0
#
# 최상위 모듈 tt_um_jameshfj01_tiny_ai_chip 테스트. 칩의 핀만 사용한다
# (게이트 수준 테스트 gl_test 에서도 그대로 돌아가야 하므로 내부 신호는 보지 않는다).
#
# 핀 사용법:
#   ui_in[7:0]  : 쓸 데이터 1바이트 (부호 있는 8비트)
#   uio_in[3:0] : 주소
#   uio_in[4]   : write. 0 -> 1 로 올라갈 때 한 번 저장한다.
#   uio_in[5]   : start. 0 -> 1 로 올라갈 때 계산을 한 번 시작한다.
#   uio_out[7]  : done. 계산이 끝나면 1, 다음 start 까지 유지.
#   uo_out[7:0] : 주소가 가리키는 결과 바이트
#
# 쓰기 주소: 0..3 = A00 A01 A10 A11, 4..7 = B00 B01 B10 B11
# 읽기 주소: {칸 번호(2비트), 바이트 번호(2비트)}
#   칸 번호 0..3 = C00 C01 C10 C11, 바이트 0 = 하위, 1 = 중간, 2 = 상위(부호 확장), 3 = 항상 0
#
# write 와 start 는 칩 바깥(예: 데모 보드의 RP2040)에서 오는 신호라서 칩 안에서
# 2단 동기화를 거친다. 그래서 각 신호를 몇 클럭 동안 유지해 준다.

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge

WRITE = 1 << 4
START = 1 << 5
DONE = 1 << 7
HOLD = 4          # write/start 를 유지하는 클럭 수 (동기화 2클럭 + 여유)
DONE_TIMEOUT = 50


def matmul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(2)) for j in range(2)] for i in range(2)]


async def start_chip(dut):
    dut._log.info("Start")
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())  # 50 MHz, config.json 과 같다
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    await FallingEdge(dut.clk)


async def write_byte(dut, addr, value):
    dut.ui_in.value = value & 0xFF
    dut.uio_in.value = addr
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = addr | WRITE
    await ClockCycles(dut.clk, HOLD)
    dut.uio_in.value = addr
    await ClockCycles(dut.clk, HOLD)


async def load(dut, A, B):
    values = [A[0][0], A[0][1], A[1][0], A[1][1], B[0][0], B[0][1], B[1][0], B[1][1]]
    for addr, v in enumerate(values):
        await write_byte(dut, addr, v)


def done(dut):
    return (int(dut.uio_out.value) & DONE) != 0


async def run(dut):
    """start 를 한 번 올렸다 내리고 done 이 될 때까지 기다린다."""
    dut.uio_in.value = START
    await ClockCycles(dut.clk, HOLD)
    dut.uio_in.value = 0
    for _ in range(DONE_TIMEOUT):
        await FallingEdge(dut.clk)
        if done(dut):
            return
    raise AssertionError("done 이 올라오지 않았다")


async def read_byte(dut, addr):
    dut.uio_in.value = addr
    await FallingEdge(dut.clk)
    return int(dut.uo_out.value)


async def read_c(dut):
    C = [[0, 0], [0, 0]]
    for cell in range(4):
        raw = 0
        for byte in range(3):
            raw |= await read_byte(dut, (cell << 2) | byte) << (8 * byte)
        if raw & (1 << 23):
            raw -= 1 << 24
        C[cell // 2][cell % 2] = raw
    return C


async def matmul_on_chip(dut, A, B):
    await load(dut, A, B)
    await run(dut)
    return await read_c(dut)


@cocotb.test()
async def test_pins_after_reset(dut):
    """리셋 후: done = 0, uio[7] 만 출력, 결과는 0."""
    await start_chip(dut)
    assert int(dut.uio_oe.value) == 0x80
    assert not done(dut)
    assert await read_c(dut) == [[0, 0], [0, 0]]


@cocotb.test()
async def test_known_example(dut):
    """[[1,2],[3,4]] x [[5,6],[7,8]] = [[19,22],[43,50]]."""
    await start_chip(dut)
    dut._log.info("Test project behavior")
    assert await matmul_on_chip(dut, [[1, 2], [3, 4]], [[5, 6], [7, 8]]) == [[19, 22], [43, 50]]


@cocotb.test()
async def test_signed_and_worst_case(dut):
    """음수와 끝값. 3바이트로 읽은 값이 18비트 결과와 정확히 같아야 한다."""
    await start_chip(dut)
    A, B = [[-1, 2], [3, -4]], [[5, -6], [-7, 8]]
    assert await matmul_on_chip(dut, A, B) == [[-19, 22], [43, -50]]
    M = [[-128, -128], [-128, -128]]
    assert await matmul_on_chip(dut, M, M) == [[32768] * 2] * 2
    P = [[127, 127], [127, 127]]
    assert await matmul_on_chip(dut, M, P) == [[-32512] * 2] * 2


@cocotb.test()
async def test_done_behaviour(dut):
    """done 은 계산이 끝난 뒤에만 1. start 를 오래 누르고 있어도 한 번만 계산한다."""
    await start_chip(dut)
    await load(dut, [[1, 1], [1, 1]], [[1, 1], [1, 1]])
    assert not done(dut)
    dut.uio_in.value = START
    seen_done = False
    for _ in range(40):
        await FallingEdge(dut.clk)
        if done(dut):
            seen_done = True
        elif seen_done:
            raise AssertionError("start 를 누르고 있는 동안 done 이 다시 내려갔다 (계산이 반복됨)")
    assert seen_done
    dut.uio_in.value = 0
    assert await read_c(dut) == [[2, 2], [2, 2]]


@cocotb.test()
async def test_unused_read_bytes(dut):
    """바이트 번호 3 (주소 3, 7, 11, 15) 은 항상 0."""
    await start_chip(dut)
    await matmul_on_chip(dut, [[-128, -128], [-128, -128]], [[-128, -128], [-128, -128]])
    for addr in (3, 7, 11, 15):
        assert await read_byte(dut, addr) == 0


@cocotb.test()
async def test_partial_reload(dut):
    """A 하나만 다시 쓰고 계산해도 나머지 값은 남아 있다."""
    await start_chip(dut)
    A, B = [[2, 0], [0, 2]], [[3, 4], [5, 6]]
    assert await matmul_on_chip(dut, A, B) == matmul(A, B)
    await write_byte(dut, 0, -1)   # A00 = -1
    A[0][0] = -1
    await run(dut)
    assert await read_c(dut) == matmul(A, B)


@cocotb.test()
async def test_random(dut):
    """무작위 행렬 20 쌍."""
    await start_chip(dut)
    rng = random.Random(7)
    for n in range(20):
        A = [[rng.randint(-128, 127) for _ in range(2)] for _ in range(2)]
        B = [[rng.randint(-128, 127) for _ in range(2)] for _ in range(2)]
        got = await matmul_on_chip(dut, A, B)
        assert got == matmul(A, B), f"#{n}: A={A} B={B} got {got}"
