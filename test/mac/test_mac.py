# SPDX-License-Identifier: Apache-2.0
#
# mac 모듈 테스트.
#
# mac은 매 클럭마다 acc <= acc + a * b 를 한다 (곱하고 누적하기).
#   a, b : 부호 있는 8비트 정수 (-128 ~ 127)
#   acc  : 부호 있는 18비트 누적값. 넘치면 2의 보수로 감긴다(wrap).
#   en   : 1일 때만 누적한다. 0이면 acc를 그대로 둔다.
#   clr  : 1이면 acc를 0으로 지운다. en보다 우선한다.
#   rst_n: 0이면 acc를 0으로 리셋한다. 가장 우선한다.
#
# 타이밍 약속: 입력은 클럭의 내려가는 엣지에서 바꾸고, 다음 내려가는 엣지에서
# 결과를 읽는다. 그 사이에 올라가는 엣지가 한 번 있어서 레지스터가 갱신된다.

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge

DATA_W = 8
ACC_W = 18


def wrap(value, bits=ACC_W):
    """정수를 bits 비트 부호 있는 2의 보수 값으로 감는다 (하드웨어와 똑같이)."""
    value &= (1 << bits) - 1
    if value >> (bits - 1):
        value -= 1 << bits
    return value


async def start(dut):
    """클럭을 켜고 리셋한 다음, 내려가는 엣지에 맞춰 멈춘다."""
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
    """입력을 걸고 클럭 한 번을 지나가게 한 뒤, acc 값을 돌려준다."""
    dut.a.value = a
    dut.b.value = b
    dut.en.value = en
    dut.clr.value = clr
    await FallingEdge(dut.clk)
    return dut.acc.value.to_signed()


@cocotb.test()
async def test_reset(dut):
    """리셋 중에는 en=1로 값을 넣어도 acc는 0이다."""
    await start(dut)
    dut.rst_n.value = 0
    for _ in range(3):
        assert await step(dut, a=5, b=5, en=1) == 0
    dut.rst_n.value = 1


@cocotb.test()
async def test_single_multiply(dut):
    """한 번 곱하기: 7 * 6 = 42."""
    await start(dut)
    assert await step(dut, a=7, b=6) == 42


@cocotb.test()
async def test_dot_product(dut):
    """여러 번 누적: [1,2,3,4] 와 [5,6,7,8] 의 내적 = 70."""
    await start(dut)
    acc = None
    for a, b in zip([1, 2, 3, 4], [5, 6, 7, 8]):
        acc = await step(dut, a=a, b=b)
    assert acc == 70


@cocotb.test()
async def test_signed(dut):
    """음수 곱셈과 8비트 끝값들."""
    await start(dut)
    cases = [
        (-3, 4, -12),
        (3, -4, -12),
        (-3, -4, 12),
        (127, 127, 16129),
        (-128, 127, -16256),
        (-128, -128, 16384),
    ]
    for a, b, expected in cases:
        await step(dut, en=0, clr=1)
        got = await step(dut, a=a, b=b)
        assert got == expected, f"{a} * {b}: got {got}, expected {expected}"


@cocotb.test()
async def test_hold_when_disabled(dut):
    """en=0이면 입력이 바뀌어도 acc는 그대로다."""
    await start(dut)
    assert await step(dut, a=10, b=10) == 100
    for a, b in [(3, 3), (-50, 20), (127, 127)]:
        assert await step(dut, a=a, b=b, en=0) == 100


@cocotb.test()
async def test_clear(dut):
    """clr=1이면 0이 되고, en=1이어도 clr이 이긴다."""
    await start(dut)
    await step(dut, a=9, b=9)
    assert await step(dut, a=9, b=9) == 162
    assert await step(dut, a=9, b=9, en=1, clr=1) == 0
    assert await step(dut, a=2, b=3) == 6


@cocotb.test()
async def test_2x2_worst_case(dut):
    """2x2 행렬곱의 한 칸은 곱 2개의 합이다. 가장 큰 경우도 18비트에 들어간다."""
    await start(dut)
    await step(dut, a=-128, b=-128)
    assert await step(dut, a=-128, b=-128) == 32768
    await step(dut, en=0, clr=1)
    await step(dut, a=-128, b=127)
    assert await step(dut, a=-128, b=127) == -32512


@cocotb.test()
async def test_overflow_wraps(dut):
    """18비트를 넘으면 2의 보수로 감긴다. 16384 * 8 = 131072 는 -131072 가 된다."""
    await start(dut)
    acc = None
    for _ in range(8):
        acc = await step(dut, a=-128, b=-128)
    assert acc == wrap(16384 * 8) == -131072


@cocotb.test()
async def test_random(dut):
    """무작위 입력 1000번을 Python 모델과 비교한다."""
    await start(dut)
    rng = random.Random(1234)
    model = 0
    lo, hi = -(1 << (DATA_W - 1)), (1 << (DATA_W - 1)) - 1
    for i in range(1000):
        a = rng.randint(lo, hi)
        b = rng.randint(lo, hi)
        en = int(rng.random() < 0.8)
        clr = int(rng.random() < 0.05)
        if clr:
            model = 0
        elif en:
            model = wrap(model + a * b)
        got = await step(dut, a=a, b=b, en=en, clr=clr)
        assert got == model, f"cycle {i}: a={a} b={b} en={en} clr={clr} got {got} expected {model}"
