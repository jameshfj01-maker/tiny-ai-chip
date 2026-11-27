# SPDX-License-Identifier: Apache-2.0
#
# mac_bitserial (+ bitserial_seq) 테스트: 완전 비트 직렬 MAC.
#
# acc 는 17비트 시프트 레지스터다. 한 클럭에 acc 의 한 비트에만 1비트 전가산기로 더한다.
#   - acc 를 한 바퀴(17 클럭) 돌리면 세로 곱셈의 한 줄 (b[i] 가 1 이면 a << i) 이 더해진다.
#   - i = 0..7 을 다 돌면 (8 x 17 = 136 클럭) acc 에 a * b 가 더해진다.
#   - b 의 부호 비트(i = 7)는 무게가 -128 이라서 그 줄은 빼기 (2의 보수: 뒤집고 +1) 를 한다.
#   - acc 는 한 바퀴가 끝날 때마다만 제자리에 있다. 그래서 값은 바퀴 끝에서 읽는다.
#   - 17비트를 넘으면 2의 보수로 감긴다.
#   - rst_n = 0 이나 clr = 1 이면 acc 와 순서 카운터가 0 이 된다. en = 0 이면 다 멈춘다.
#
# 타이밍 약속: 내려가는 엣지에서 입력을 바꾸고 다음 내려가는 엣지에서 읽는다.

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge

DATA_W = 8
ACC_W = 17
PASS = ACC_W              # acc 한 바퀴 = 17 클럭
PRODUCT = DATA_W * PASS   # 곱 하나 = 136 클럭


def wrap(value, bits=ACC_W):
    value &= (1 << bits) - 1
    if value >> (bits - 1):
        value -= 1 << bits
    return value


def row(a, b, i):
    """세로 곱셈의 i 번째 줄 (하드웨어 모델)."""
    if not ((b & 0xFF) >> i) & 1:
        return 0
    return -(a << i) if i == DATA_W - 1 else a << i


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


def acc(dut):
    return dut.acc.value.to_signed()


async def mac(dut, a, b):
    """en 136 클럭: acc += a * b. 마지막 클럭에만 last = 1 이어야 한다."""
    for k in range(PRODUCT):
        dut.a.value = a
        dut.b.value = b
        dut.en.value = 1
        dut.clr.value = 0
        await FallingEdge(dut.clk)
    return acc(dut)


async def mac_checking_last(dut, a, b):
    lasts = []
    for k in range(PRODUCT):
        dut.a.value = a
        dut.b.value = b
        dut.en.value = 1
        dut.clr.value = 0
        lasts.append(int(dut.last.value))   # 이번 클럭(올라가는 엣지 전)의 last
        await FallingEdge(dut.clk)
    return acc(dut), lasts


@cocotb.test()
async def test_reset(dut):
    """리셋 중에는 en=1 이어도 acc 는 0."""
    await start(dut)
    dut.rst_n.value = 0
    for _ in range(20):
        await step(dut, a=5, b=5)
        assert acc(dut) == 0
    dut.rst_n.value = 1


@cocotb.test()
async def test_single_multiply(dut):
    """7 * 6 = 42, 136 클럭."""
    await start(dut)
    assert await mac(dut, 7, 6) == 42


@cocotb.test()
async def test_last_pulse(dut):
    """last 는 곱 하나에 딱 한 번, 136 번째 클럭에 1 이다."""
    await start(dut)
    got, lasts = await mac_checking_last(dut, 3, 5)
    assert got == 15
    assert lasts.count(1) == 1 and lasts[-1] == 1, [k for k, v in enumerate(lasts) if v]
    got, lasts = await mac_checking_last(dut, -2, 9)
    assert got == 15 - 18
    assert lasts.count(1) == 1 and lasts[-1] == 1


@cocotb.test()
async def test_partial_rows(dut):
    """acc 가 한 바퀴(17 클럭) 돌 때마다 세로 곱셈이 한 줄씩 더해진다. 음수 b 의 마지막 줄은 빼기."""
    await start(dut)
    for a, b in [(13, 11), (-100, -77), (127, -128), (-128, -1)]:
        await step(dut, en=0, clr=1)
        expected = 0
        for i in range(DATA_W):
            for _ in range(PASS):
                await step(dut, a=a, b=b)
            expected += row(a, b, i)
            assert acc(dut) == expected, f"a={a} b={b} row {i}: got {acc(dut)} expected {expected}"
        assert expected == a * b


@cocotb.test()
async def test_signed(dut):
    """음수와 끝값."""
    await start(dut)
    cases = [(-3, 4), (3, -4), (-3, -4), (127, 127), (-128, 127), (127, -128),
             (-128, -128), (0, -128), (-1, -1), (1, -128), (-128, 1)]
    for a, b in cases:
        await step(dut, en=0, clr=1)
        got = await mac(dut, a, b)
        assert got == a * b, f"{a} * {b}: got {got}"


@cocotb.test()
async def test_two_products(dut):
    """2x2 행렬곱 한 칸은 곱 2 개의 합이다. 가장 큰 경우 32768 과 가장 작은 경우 -32512 도 17비트에 들어간다."""
    await start(dut)
    await mac(dut, -128, -128)
    assert await mac(dut, -128, -128) == 32768
    await step(dut, en=0, clr=1)
    await mac(dut, -128, 127)
    assert await mac(dut, 127, -128) == -32512


@cocotb.test()
async def test_dot_product(dut):
    """곱 4 개 누적: [1,2,3,4] . [5,6,7,8] = 70."""
    await start(dut)
    for a, b in zip([1, 2, 3, 4], [5, 6, 7, 8]):
        got = await mac(dut, a, b)
    assert got == 70


@cocotb.test()
async def test_stall_mid_product(dut):
    """곱셈 도중 아무 때나 en=0 으로 쉬어도 결과가 같다 (acc, 올림수, 카운터 모두 멈춘다)."""
    await start(dut)
    rng = random.Random(5)
    for _ in range(PRODUCT):
        await step(dut, a=-77, b=93)
        for _ in range(rng.randint(0, 2)):
            await step(dut, a=55, b=-55, en=0)
    assert acc(dut) == -77 * 93


@cocotb.test()
async def test_clear_mid_product(dut):
    """곱셈 도중(40 클럭 후)에 clr 하면 acc 와 카운터가 다 0 으로 돌아가서 다음 곱이 맞다."""
    await start(dut)
    for _ in range(40):
        await step(dut, a=-128, b=-128)
    await step(dut, a=9, b=9, en=1, clr=1)
    assert acc(dut) == 0
    assert await mac(dut, -100, 77) == -7700


@cocotb.test()
async def test_reset_mid_product(dut):
    """곱셈 도중 리셋해도 카운터가 0 으로 돌아간다."""
    await start(dut)
    for _ in range(77):
        await step(dut, a=37, b=-91)
    dut.rst_n.value = 0
    await step(dut, en=0)
    dut.rst_n.value = 1
    assert await mac(dut, 37, -91) == 37 * -91


@cocotb.test()
async def test_overflow_wraps(dut):
    """17비트를 넘으면 감긴다: 16384 * 4 = 65536 -> -65536."""
    await start(dut)
    for _ in range(4):
        got = await mac(dut, -128, -128)
    assert got == wrap(16384 * 4) == -65536


@cocotb.test()
async def test_random(dut):
    """무작위 곱 150 개 (가끔 clr) 를 Python 모델과 비교한다."""
    await start(dut)
    rng = random.Random(1234)
    model = 0
    for n in range(150):
        if rng.random() < 0.3:
            await step(dut, en=0, clr=1)
            model = 0
        a = rng.randint(-128, 127)
        b = rng.randint(-128, 127)
        model = wrap(model + a * b)
        got = await mac(dut, a, b)
        assert got == model, f"#{n}: a={a} b={b} got {got} expected {model}"
