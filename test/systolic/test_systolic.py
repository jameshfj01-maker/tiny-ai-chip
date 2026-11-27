# SPDX-License-Identifier: Apache-2.0
#
# systolic_2x2 모듈 테스트: C = A x B (A, B 는 2x2, 원소는 부호 있는 8비트).
#
# 배열 모양 (output stationary: 결과 C 는 각 칸에 머물고, A 와 B 가 흘러간다):
#
#              b_in0        b_in1
#                |            |
#   a_in0 ---> [PE00] -----> [PE01]
#                |            |
#   a_in1 ---> [PE10] -----> [PE11]
#
#   A 는 왼쪽에서 오른쪽으로, B 는 위에서 아래로 한 클럭에 한 칸씩 이동한다.
#   PE(i,j) 는 C[i][j] = A[i][0]*B[0][j] + A[i][1]*B[1][j] 를 누적한다.
#
# 입력 일정 (비스듬하게 밀어 넣기, skew):
#   시각 t 에 a_in[i] = A[i][t-i], b_in[j] = B[t-j][j]  (범위 밖이면 0)
#
#   t:       0     1     2     3
#   a_in0:  A00   A01    0     0
#   a_in1:   0    A10   A11    0
#   b_in0:  B00   B10    0     0
#   b_in1:   0    B01   B11    0
#
#   PE(i,j) 는 시각 t = i + j + k 에 k 번째 곱을 받는다. 그래서 4 박자면 끝난다.
#
# 박자(beat): 각 PE 는 완전 비트 직렬 MAC 이라서 곱 하나에 8 줄 x 17 비트 = 136 클럭이 걸린다.
#   한 박자 = en 136 클럭. 그동안 a_in, b_in 을 그대로 둔다. 순서는 배열 안의 지휘자가 센다.
#   이동 레지스터(a, b 를 이웃 PE 로 넘기는 것)는 박자의 마지막 클럭에만 움직이고,
#   그 클럭에 beat_end 출력이 1 이 된다.
#   그래서 행렬곱 한 번 = 4 박자 = 544 클럭.
#
# 타이밍 약속은 mac 테스트와 같다: 내려가는 엣지에서 입력을 바꾸고 다음
# 내려가는 엣지에서 결과를 읽는다.

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, Timer

N = 2          # 행렬 크기
CYCLES = 4     # 행렬곱 한 번에 필요한 박자 수 = N + 2*(N-1)
BITS = 8 * 17  # 한 박자의 클럭 수 (완전 비트 직렬 MAC 이 곱 하나에 쓰는 클럭 = 136)
ACC_W = 17


def matmul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(N)) for j in range(N)] for i in range(N)]


def schedule(A, B, t):
    """시각 t 에 넣을 (a_in0, a_in1, b_in0, b_in1)."""
    def a_at(i):
        k = t - i
        return A[i][k] if 0 <= k < N else 0

    def b_at(j):
        k = t - j
        return B[k][j] if 0 <= k < N else 0

    return a_at(0), a_at(1), b_at(0), b_at(1)


def read_c(dut):
    return [
        [dut.c00.value.to_signed(), dut.c01.value.to_signed()],
        [dut.c10.value.to_signed(), dut.c11.value.to_signed()],
    ]


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for name in ("en", "clr", "a_in0", "a_in1", "b_in0", "b_in1"):
        getattr(dut, name).value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1


async def step(dut, a0=0, a1=0, b0=0, b1=0, en=1, clr=0):
    """클럭 한 번."""
    dut.a_in0.value = a0
    dut.a_in1.value = a1
    dut.b_in0.value = b0
    dut.b_in1.value = b1
    dut.en.value = en
    dut.clr.value = clr
    await FallingEdge(dut.clk)


async def beat(dut, a0, a1, b0, b1):
    """박자 한 번: 같은 입력을 en 8 클럭 동안 둔다."""
    for _ in range(BITS):
        await step(dut, a0, a1, b0, b1, en=1)


async def run_matmul(dut, A, B):
    """clr 한 번 후 4 박자 동안 일정대로 넣고, 결과 C 를 돌려준다."""
    await step(dut, en=0, clr=1)
    for t in range(CYCLES):
        await beat(dut, *schedule(A, B, t))
    await step(dut, en=0)   # 한 클럭 쉬어도 결과가 그대로인지도 함께 본다
    return read_c(dut)


@cocotb.test()
async def test_reset(dut):
    """리셋 후 결과는 모두 0."""
    await start(dut)
    assert read_c(dut) == [[0, 0], [0, 0]]


@cocotb.test()
async def test_known_example(dut):
    """[[1,2],[3,4]] x [[5,6],[7,8]] = [[19,22],[43,50]]."""
    await start(dut)
    assert await run_matmul(dut, [[1, 2], [3, 4]], [[5, 6], [7, 8]]) == [[19, 22], [43, 50]]


@cocotb.test()
async def test_identity(dut):
    """A x I = A, I x B = B."""
    await start(dut)
    I = [[1, 0], [0, 1]]
    A = [[-7, 13], [100, -128]]
    assert await run_matmul(dut, A, I) == A
    assert await run_matmul(dut, I, A) == A


@cocotb.test()
async def test_signed(dut):
    """음수가 섞인 행렬."""
    await start(dut)
    A = [[-1, 2], [3, -4]]
    B = [[5, -6], [-7, 8]]
    assert await run_matmul(dut, A, B) == matmul(A, B) == [[-19, 22], [43, -50]]


@cocotb.test()
async def test_worst_case(dut):
    """끝값끼리 곱해도 18비트 안에 정확히 들어간다."""
    await start(dut)
    M = [[-128, -128], [-128, -128]]
    assert await run_matmul(dut, M, M) == [[32768, 32768], [32768, 32768]]
    P = [[127, 127], [127, 127]]
    assert await run_matmul(dut, M, P) == [[-32512, -32512], [-32512, -32512]]


@cocotb.test()
async def test_back_to_back(dut):
    """연속 두 번 계산해도 앞 계산의 찌꺼기가 남지 않는다 (clr 가 이동 레지스터까지 지운다)."""
    await start(dut)
    A1, B1 = [[9, 8], [7, 6]], [[5, 4], [3, 2]]
    A2, B2 = [[1, -1], [-1, 1]], [[2, 3], [4, 5]]
    assert await run_matmul(dut, A1, B1) == matmul(A1, B1)
    assert await run_matmul(dut, A2, B2) == matmul(A2, B2)


@cocotb.test()
async def test_stall(dut):
    """비트마다 en=0 으로 멈췄다가 이어가도 결과가 같다.
    멈춘 동안 입력에 쓰레기가 있어도 무시해야 한다 (카운터와 이동 레지스터도 그대로)."""
    await start(dut)
    A, B = [[3, -5], [11, 2]], [[-4, 6], [1, 9]]
    await step(dut, en=0, clr=1)
    for t in range(CYCLES):
        for _ in range(BITS):
            await step(dut, *schedule(A, B, t), en=1)
            await step(dut, 99, -99, 55, -55, en=0)
    assert read_c(dut) == matmul(A, B)


@cocotb.test()
async def test_pass_registers_move_once_per_beat(dut):
    """이동 레지스터가 박자 중간에 움직이면 PE01 이 엉뚱한 a 를 받는다.
    A = [[2,0],[0,0]], B = [[0,3],[0,0]] 이면 C01 = 2*3 = 6 만 0 이 아니다."""
    await start(dut)
    A, B = [[2, 0], [0, 0]], [[0, 3], [0, 0]]
    assert await run_matmul(dut, A, B) == [[0, 6], [0, 0]]


@cocotb.test()
async def test_clr_mid_matmul(dut):
    """계산 도중(1.5 박자 뒤)에 clr 하고 새로 시작해도 결과가 맞다 (카운터와 이동 레지스터가 다 지워진다)."""
    await start(dut)
    A1, B1 = [[-128, 127], [5, 6]], [[7, -8], [9, 10]]
    await step(dut, en=0, clr=1)
    await beat(dut, *schedule(A1, B1, 0))
    for _ in range(4):
        await step(dut, *schedule(A1, B1, 1), en=1)
    A2, B2 = [[1, 2], [3, 4]], [[5, 6], [7, 8]]
    assert await run_matmul(dut, A2, B2) == [[19, 22], [43, 50]]


@cocotb.test()
async def test_beat_end_output(dut):
    """beat_end 는 박자마다 한 번, 박자의 마지막 클럭에만 1 이다. en = 0 이면 0."""
    await start(dut)
    A, B = [[1, 2], [3, 4]], [[5, 6], [7, 8]]
    await step(dut, en=0, clr=1)
    for t in range(CYCLES):
        ends = []
        for _ in range(BITS):
            a0, a1, b0, b1 = schedule(A, B, t)
            dut.a_in0.value = a0
            dut.a_in1.value = a1
            dut.b_in0.value = b0
            dut.b_in1.value = b1
            dut.en.value = 1
            dut.clr.value = 0
            await Timer(1, unit="ns")
            ends.append(int(dut.beat_end.value))
            await FallingEdge(dut.clk)
        assert ends.count(1) == 1 and ends[-1] == 1, f"beat {t}: {[k for k, v in enumerate(ends) if v]}"
    dut.en.value = 0
    await Timer(1, unit="ns")
    assert int(dut.beat_end.value) == 0
    assert read_c(dut) == [[19, 22], [43, 50]]


@cocotb.test()
async def test_wavefront(dut):
    """매 박자 중간 결과를 본다. PE(i,j) 는 박자 i+j+k 에 k 번째 곱을 더한다 (대각선 물결)."""
    await start(dut)
    A, B = [[1, 2], [3, 4]], [[5, 6], [7, 8]]
    await step(dut, en=0, clr=1)
    for t in range(CYCLES):
        await beat(dut, *schedule(A, B, t))
        expected = [
            [sum(A[i][k] * B[k][j] for k in range(N) if i + j + k <= t) for j in range(N)]
            for i in range(N)
        ]
        assert read_c(dut) == expected, f"t={t}: got {read_c(dut)}, expected {expected}"


@cocotb.test()
async def test_random(dut):
    """무작위 행렬 40 쌍을 Python 행렬곱과 비교한다."""
    await start(dut)
    rng = random.Random(2026)
    for n in range(40):
        A = [[rng.randint(-128, 127) for _ in range(N)] for _ in range(N)]
        B = [[rng.randint(-128, 127) for _ in range(N)] for _ in range(N)]
        got = await run_matmul(dut, A, B)
        assert got == matmul(A, B), f"#{n}: A={A} B={B} got {got}"
