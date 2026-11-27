# SPDX-License-Identifier: Apache-2.0
#
# mac_serial 모듈 테스트: 비트 직렬 MAC.
#
# a * b 를 한 클럭에 한 번 계산하지 않고, b 의 비트 하나씩 8 클럭에 나눠서 더한다.
#   MAC 안에 비트 번호를 세는 작은 카운터(0..7)가 있다.
#   en = 1 인 클럭마다: b[비트 번호] 가 1 이면 acc 에 (a << 비트 번호) 를 더하고, 카운터가 1 늘어난다.
#   단, 비트 7 (부호 비트) 은 무게가 -128 이라서 더하지 않고 뺀다.
#   카운터는 7 다음에 0 으로 돌아가서, en 8 번마다 곱 하나가 끝난다.
#   clr 와 rst_n 은 acc 와 카운터를 둘 다 0 으로 만든다.
#
#   a, b : 부호 있는 8비트, acc : 부호 있는 18비트 (넘치면 2의 보수로 감긴다)
#   rst_n = 0 이면 acc = 0, clr = 1 이면 acc = 0 (en 보다 우선)
#
# 타이밍 약속은 mac 테스트와 같다: 내려가는 엣지에서 입력을 바꾸고, 다음
# 내려가는 엣지에서 결과를 읽는다.

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge

DATA_W = 8
ACC_W = 18


def wrap(value, bits=ACC_W):
    value &= (1 << bits) - 1
    if value >> (bits - 1):
        value -= 1 << bits
    return value


def bit_term(a, b, i):
    """비트 번호 i 를 처리하는 클럭 한 번에 acc 에 더해지는 값 (하드웨어 모델)."""
    bit = ((b & 0xFF) >> i) & 1        # b 의 i 번째 비트 (2의 보수 그대로)
    if not bit:
        return 0
    if i == DATA_W - 1:                 # 부호 비트: 무게가 -2^7
        return -(a << i)
    return a << i


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.en.value = 0
    dut.clr.value = 0
    dut.a.value = 0
    dut.b.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1


async def step(dut, a=0, b=0, en=1, clr=0):
    dut.a.value = a
    dut.b.value = b
    dut.en.value = en
    dut.clr.value = clr
    await FallingEdge(dut.clk)
    return dut.acc.value.to_signed()


async def mac8(dut, a, b):
    """en 8 클럭: b 의 비트 8개를 차례로 처리해서 acc += a * b 를 한다."""
    acc = None
    for _ in range(DATA_W):
        acc = await step(dut, a=a, b=b)
    return acc


@cocotb.test()
async def test_reset(dut):
    """리셋 중에는 en=1 이어도 acc 는 0."""
    await start(dut)
    dut.rst_n.value = 0
    for _ in range(DATA_W):
        assert await step(dut, a=5, b=5) == 0
    dut.rst_n.value = 1


@cocotb.test()
async def test_single_multiply(dut):
    """7 * 6 = 42 를 8 클럭에 걸쳐 계산한다."""
    await start(dut)
    assert await mac8(dut, 7, 6) == 42


@cocotb.test()
async def test_partial_sums(dut):
    """비트 하나 처리할 때마다 중간값이 세로 곱셈의 한 줄씩 늘어난다.
    a = 13, b = 0b0000_1011 (11): 13, 13+26=39, 39, 39+104=143, ... 143."""
    await start(dut)
    a, b = 13, 11
    expected = 0
    for i in range(DATA_W):
        expected += bit_term(a, b, i)
        got = await step(dut, a=a, b=b)
        assert got == expected, f"bit {i}: got {got}, expected {expected}"
    assert expected == 143


@cocotb.test()
async def test_signed(dut):
    """음수와 끝값. b 가 음수면 마지막 비트(부호 비트)에서 빼기가 일어난다."""
    await start(dut)
    cases = [
        (-3, 4, -12),
        (3, -4, -12),
        (-3, -4, 12),
        (127, 127, 16129),
        (-128, 127, -16256),
        (127, -128, -16256),
        (-128, -128, 16384),
        (0, -128, 0),
        (-1, -1, 1),
    ]
    for a, b, expected in cases:
        await step(dut, en=0, clr=1)
        got = await mac8(dut, a, b)
        assert got == expected, f"{a} * {b}: got {got}, expected {expected}"


@cocotb.test()
async def test_dot_product(dut):
    """곱 4개 누적: [1,2,3,4] . [5,6,7,8] = 70, 그리고 음수가 섞인 경우."""
    await start(dut)
    acc = None
    for a, b in zip([1, 2, 3, 4], [5, 6, 7, 8]):
        acc = await mac8(dut, a, b)
    assert acc == 70
    await step(dut, en=0, clr=1)
    for a, b in zip([-128, 127, -5, 100], [-128, -128, 9, -77]):
        acc = await mac8(dut, a, b)
    assert acc == 16384 - 16256 - 45 - 7700


@cocotb.test()
async def test_hold_when_disabled(dut):
    """en=0 이면 입력이 바뀌어도 acc 는 그대로 (카운터도 멈춘다)."""
    await start(dut)
    assert await mac8(dut, 10, 10) == 100
    for _ in range(DATA_W):
        assert await step(dut, a=-128, b=-1, en=0) == 100
    assert await mac8(dut, 3, 4) == 112


@cocotb.test()
async def test_stall_mid_product(dut):
    """곱셈 도중에 en=0 으로 쉬었다가 이어가도 결과가 같다 (쉬는 동안 카운터도 멈춘다)."""
    await start(dut)
    acc = None
    for _ in range(DATA_W):
        acc = await step(dut, a=-77, b=93)
        await step(dut, a=55, b=-55, en=0)
    assert acc == -77 * 93


@cocotb.test()
async def test_clear(dut):
    """clr=1 이면 0 이 되고, en=1 이어도 clr 이 이긴다."""
    await start(dut)
    await mac8(dut, 9, 9)
    assert await step(dut, a=9, b=9, en=1, clr=1) == 0
    assert await mac8(dut, 2, 3) == 6


@cocotb.test()
async def test_overflow_wraps(dut):
    """18비트를 넘으면 감긴다: 16384 * 8 = 131072 -> -131072."""
    await start(dut)
    acc = None
    for _ in range(8):
        acc = await mac8(dut, -128, -128)
    assert acc == wrap(16384 * 8) == -131072


@cocotb.test()
async def test_clr_restarts_bit_counter(dut):
    """곱셈 도중(3 비트 처리 후)에 clr 하면 카운터도 0 으로 돌아가서 다음 곱이 맞게 나온다."""
    await start(dut)
    for _ in range(3):
        await step(dut, a=-128, b=-128)
    await step(dut, en=0, clr=1)
    assert await mac8(dut, -100, 77) == -7700


@cocotb.test()
async def test_reset_restarts_bit_counter(dut):
    """곱셈 도중에 리셋해도 카운터가 0 으로 돌아간다."""
    await start(dut)
    for _ in range(5):
        await step(dut, a=37, b=-91)
    dut.rst_n.value = 0
    await step(dut, en=0)
    dut.rst_n.value = 1
    assert await mac8(dut, 37, -91) == 37 * -91


@cocotb.test()
async def test_random(dut):
    """무작위 곱 300개를 무작위 clr 와 함께 Python 모델과 비교한다."""
    await start(dut)
    rng = random.Random(1234)
    model = 0
    for n in range(300):
        if rng.random() < 0.2:
            await step(dut, en=0, clr=1)
            model = 0
        a = rng.randint(-128, 127)
        b = rng.randint(-128, 127)
        model = wrap(model + a * b)
        got = await mac8(dut, a, b)
        assert got == model, f"#{n}: a={a} b={b} got {got} expected {model}"
