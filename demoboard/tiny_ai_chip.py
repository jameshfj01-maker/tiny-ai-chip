# SPDX-License-Identifier: Apache-2.0
#
# tiny_ai_chip.py: Tiny Tapeout 데모 보드에서 실제 칩을 시험하는 스크립트 (MicroPython).
#
# 칩: tt_um_jameshfj01_tiny_ai_chip (2x2 int8 행렬곱, systolic array)
# 사용법과 순서는 demoboard/README.md 에 있다. 보드에서는:
#
#     import tiny_ai_chip
#     tiny_ai_chip.main()
#
# 구조: 시험 논리(Chip, run_all)는 "보드" 객체만 쓴다. 보드는 아래 6 가지만 하면 된다.
#     set_ui(v), set_uio(v), get_uo(), get_uio(), wait_clocks(n), reset()
#   - TTBoardAdapter: 진짜 데모 보드 (ttboard SDK 사용)
#   - test/demoboard 의 SimBoard: RTL 시뮬레이션 (칩이 오기 전에 이 스크립트를 확인하는 용도)
# 그래서 이 파일은 MicroPython 과 보통 파이썬 둘 다에서 돌아가야 한다.

# ---------------------------------------------------------------------------
# 핀 약속 (docs/info.md 와 같다)
# ---------------------------------------------------------------------------
PROJECT_NAME = "tt_um_jameshfj01_tiny_ai_chip"

WRITE = 0x10            # uio[4]
START = 0x20            # uio[5]
ACC = 0x40              # uio[6]: start 할 때 1 이면 더하기 모드 (C = C + A x B)
DONE = 0x80             # uio[7] (칩이 내보내는 핀)

# 데모 보드(Pico)가 내보낼 uio 핀: uio[6:0]. uio[7] 은 칩이 내보내므로 절대 Pico 가 내보내면 안 된다.
UIO_PICO_OUTPUTS = 0x7F
UIO_CHIP_OUTPUTS = 0x80  # 칩의 uio_oe 가 이 값이어야 한다

HOLD_CLOCKS = 4          # write / start 를 유지하는 클럭 수 (칩 안 동기화 2 클럭 + 여유)
COMPUTE_CLOCKS = 576     # 계산 클럭 수: 4 박자 x 144 클럭 (완전 비트 직렬 MAC)
DONE_TIMEOUT = 1000      # done 을 기다리는 최대 횟수 (정상은 약 580 클럭)


def matmul_ref(A, B):
    """정답: 파이썬으로 계산한 n x n 행렬곱."""
    n = len(A)
    return [[sum(A[i][k] * B[k][j] for k in range(n)) for j in range(n)] for i in range(n)]


def block(M, bi, bj):
    """4x4 행렬 M 의 (bi, bj) 번째 2x2 블록."""
    return [[M[2 * bi + i][2 * bj + j] for j in range(2)] for i in range(2)]


class Lcg:
    """간단한 의사 난수 (MicroPython 과 보통 파이썬에서 똑같은 값이 나오게 직접 만든다)."""

    def __init__(self, seed):
        self.x = seed & 0x7FFFFFFF

    def int8(self):
        self.x = (1103515245 * self.x + 12345) & 0x7FFFFFFF
        return ((self.x >> 16) & 0xFF) - 128


class Chip:
    """칩을 핀으로 다루는 방법 (write, start, read). 보드 종류와 상관없다."""

    def __init__(self, board, hold_clocks=HOLD_CLOCKS, done_timeout=DONE_TIMEOUT):
        self.board = board
        self.hold = hold_clocks
        self.timeout = done_timeout

    def write_byte(self, addr, value):
        """주소 addr (0..7) 에 값 하나 (-128..127) 를 저장한다. write 를 올렸다가 내린다."""
        b = self.board
        b.set_ui(value & 0xFF)
        b.set_uio(addr)
        b.wait_clocks(1)
        b.set_uio(addr | WRITE)
        b.wait_clocks(self.hold)
        b.set_uio(addr)
        b.wait_clocks(self.hold)

    def load(self, A, B):
        values = [A[0][0], A[0][1], A[1][0], A[1][1], B[0][0], B[0][1], B[1][0], B[1][1]]
        for addr in range(8):
            self.write_byte(addr, values[addr])

    def done(self):
        return (self.board.get_uio() & DONE) != 0

    def run(self, accumulate=False):
        """start 를 한 번 누르고 done 을 기다린다. start 부터 done 까지 기다린 클럭 수를 돌려준다.
        accumulate 면 acc 핀(uio[6])도 같이 1 로 해서 이전 결과에 더한다."""
        b = self.board
        b.set_uio(START | (ACC if accumulate else 0))
        clocks = 0
        for _ in range(self.hold):
            b.wait_clocks(1)
            clocks += 1
        b.set_uio(0)
        while not self.done():
            if clocks >= self.timeout:
                raise RuntimeError("done 이 올라오지 않았다")
            b.wait_clocks(1)
            clocks += 1
        return clocks

    def read_byte(self, addr):
        b = self.board
        b.set_uio(addr)
        b.wait_clocks(1)
        return b.get_uo()

    def read_c(self):
        """결과 C (2x2) 를 읽는다. 칸마다 3 바이트를 이어서 24비트 부호 있는 수로 만든다."""
        C = [[0, 0], [0, 0]]
        for cell in range(4):
            raw = 0
            for byte in range(3):
                raw |= self.read_byte((cell << 2) | byte) << (8 * byte)
            if raw & 0x800000:
                raw -= 0x1000000
            C[cell // 2][cell % 2] = raw
        return C

    def matmul(self, A, B, accumulate=False):
        self.load(A, B)
        self.run(accumulate)
        return self.read_c()

    def matmul4(self, A, B):
        """4x4 행렬곱을 2x2 블록으로 나눠 계산한다.
        C 의 블록 (bi, bj) = A(bi,0) x B(0,bj) + A(bi,1) x B(1,bj): 첫 곱은 보통, 둘째는 더하기 모드."""
        C = [[0] * 4 for _ in range(4)]
        for bi in range(2):
            for bj in range(2):
                self.matmul(block(A, bi, 0), block(B, 0, bj))
                part = self.matmul(block(A, bi, 1), block(B, 1, bj), accumulate=True)
                for i in range(2):
                    for j in range(2):
                        C[2 * bi + i][2 * bj + j] = part[i][j]
        return C


# ---------------------------------------------------------------------------
# 시험 목록 (cocotb 테스트 test/test.py 와 같은 값)
# ---------------------------------------------------------------------------
M = [[-128, -128], [-128, -128]]
P = [[127, 127], [127, 127]]
CASES = [
    ("알려진 예시", [[1, 2], [3, 4]], [[5, 6], [7, 8]]),
    ("단위행렬", [[-7, 13], [100, -128]], [[1, 0], [0, 1]]),
    ("음수 섞임", [[-1, 2], [3, -4]], [[5, -6], [-7, 8]]),
    ("끝값 -128 x -128", M, M),
    ("끝값 -128 x 127", M, P),
    ("끝값 127 x 127", P, P),
    ("0 행렬", [[0, 0], [0, 0]], [[-128, 127], [55, -1]]),
]


def run_all(chip, log=print, n_random=20, check_clocks=None):
    """모든 시험을 돌리고 {"passed", "failed", "total"} 를 돌려준다.
    check_clocks: start 부터 done 까지 클럭 수도 확인할지 (수동 클럭일 때만 정확하다).
    None 이면 보드의 exact_clocks 를 따른다."""
    if check_clocks is None:
        check_clocks = getattr(chip.board, "exact_clocks", False)
    result = {"passed": 0, "failed": 0, "total": 0}

    def check(name, ok, detail=""):
        result["total"] += 1
        if ok:
            result["passed"] += 1
            log("PASS  " + name)
        else:
            result["failed"] += 1
            log("FAIL  " + name + "  " + detail)

    b = chip.board
    b.reset()

    # 1. 리셋 직후 핀 상태
    if hasattr(b, "get_uio_oe"):
        oe = b.get_uio_oe()
        check("uio_oe = 0x80 (uio[7] 만 칩 출력)", oe == UIO_CHIP_OUTPUTS, "uio_oe=0x%02x" % oe)
    check("리셋 후 done = 0", not chip.done())
    C = chip.read_c()
    check("리셋 후 결과 = 0", C == [[0, 0], [0, 0]], "got %s" % C)

    # 2. 계산 시간
    chip.load([[1, 2], [3, 4]], [[5, 6], [7, 8]])
    clocks = chip.run()
    if check_clocks:
        check("start -> done 클럭 수 %d..%d" % (COMPUTE_CLOCKS, COMPUTE_CLOCKS + 8),
              COMPUTE_CLOCKS <= clocks <= COMPUTE_CLOCKS + 8, "clocks=%d" % clocks)
    else:
        log("INFO  start -> done 대기 %d 번" % clocks)
    check("done 이 1 로 유지", chip.done())

    # 3. 정해진 예시들
    for name, A, B in CASES:
        got = chip.matmul(A, B)
        want = matmul_ref(A, B)
        check(name, got == want, "A=%s B=%s got %s want %s" % (A, B, got, want))

    # 4. 읽기 주소 3, 7, 11, 15 는 항상 0
    zeros = [chip.read_byte(addr) for addr in (3, 7, 11, 15)]
    check("안 쓰는 읽기 주소 = 0", zeros == [0, 0, 0, 0], "got %s" % zeros)

    # 5. 일부만 다시 쓰기: A00 만 바꿔도 나머지 값은 남아 있다
    A, B = [[2, 0], [0, 2]], [[3, 4], [5, 6]]
    chip.matmul(A, B)
    chip.write_byte(0, -1)
    A[0][0] = -1
    chip.run()
    got = chip.read_c()
    check("A00 만 다시 쓰기", got == matmul_ref(A, B), "got %s" % got)

    # 6. 더하기 모드: C = A1 x B1 + A2 x B2, 그다음 보통 start 는 다시 새로 계산
    A1, B1 = [[1, 2], [3, 4]], [[5, 6], [7, 8]]
    A2, B2 = [[-9, 10], [11, -12]], [[13, 14], [-15, 16]]
    chip.matmul(A1, B1)
    got = chip.matmul(A2, B2, accumulate=True)
    want = [[matmul_ref(A1, B1)[i][j] + matmul_ref(A2, B2)[i][j] for j in range(2)] for i in range(2)]
    again = chip.matmul(A1, B1)
    check("더하기 모드", got == want and again == matmul_ref(A1, B1), "got %s then %s" % (got, again))

    # 7. 4x4 행렬곱 (2x2 블록 8 번)
    A = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16]]
    B = [[1, 0, 0, 1], [0, 1, 1, 0], [-1, 0, 2, 0], [0, -2, 0, 3]]
    got = chip.matmul4(A, B)
    check("4x4 예시", got == matmul_ref(A, B), "got %s" % got)
    M4 = [[-128] * 4 for _ in range(4)]
    got = chip.matmul4(M4, M4)
    check("4x4 끝값 (칸마다 65536)", got == [[65536] * 4 for _ in range(4)], "got %s" % got)

    # 8. 무작위
    rng = Lcg(2026)
    bad = 0
    for n in range(n_random):
        A = [[rng.int8(), rng.int8()], [rng.int8(), rng.int8()]]
        B = [[rng.int8(), rng.int8()], [rng.int8(), rng.int8()]]
        got = chip.matmul(A, B)
        if got != matmul_ref(A, B):
            bad += 1
            log("      #%d A=%s B=%s got %s want %s" % (n, A, B, got, matmul_ref(A, B)))
    check("무작위 %d 쌍" % n_random, bad == 0, "%d 개 틀림" % bad)

    # 9. 무작위 4x4
    bad = 0
    for n in range(2):
        A = [[rng.int8() for _ in range(4)] for _ in range(4)]
        B = [[rng.int8() for _ in range(4)] for _ in range(4)]
        if chip.matmul4(A, B) != matmul_ref(A, B):
            bad += 1
    check("무작위 4x4 2 쌍", bad == 0, "%d 개 틀림" % bad)

    log("결과: %d / %d 통과" % (result["passed"], result["total"]))
    return result


# ---------------------------------------------------------------------------
# 진짜 데모 보드 (MicroPython 에서만 쓴다)
# ---------------------------------------------------------------------------
class TTBoardAdapter:
    """ttboard SDK 로 데모 보드의 핀을 움직인다.
    freq = None 이면 수동 클럭 (clock_project_once), 숫자면 그 주파수로 계속 클럭을 준다."""

    def __init__(self, project=PROJECT_NAME):
        from ttboard.demoboard import DemoBoard
        from ttboard.mode import RPMode

        self.tt = DemoBoard.get()
        self.tt.mode = RPMode.ASIC_RP_CONTROL     # Pico 가 ui_in 을 내보내는 모드
        getattr(self.tt.shuttle, project).enable()
        self.tt.uio_oe_pico.value = UIO_PICO_OUTPUTS  # uio[6:0] 만 Pico 출력, uio[7] 은 입력으로 둔다
        self.freq = None
        self.exact_clocks = True
        self.tt.clock_project_stop()

    def set_clock(self, freq):
        """None: 수동 클럭. 숫자: 그 주파수(Hz)로 자동 클럭."""
        self.freq = freq
        self.exact_clocks = freq is None
        if freq is None:
            self.tt.clock_project_stop()
        else:
            self.tt.clock_project_PWM(freq)

    def set_ui(self, value):
        self.tt.ui_in.value = value & 0xFF

    def set_uio(self, value):
        self.tt.uio_in.value = value & UIO_PICO_OUTPUTS

    def get_uo(self):
        return int(self.tt.uo_out.value)

    def get_uio(self):
        return int(self.tt.uio_out.value)

    def wait_clocks(self, n):
        if self.freq is None:
            for _ in range(n):
                self.tt.clock_project_once()
        else:
            import time
            # 클럭이 저절로 돌고 있으니 n 클럭 이상 걸리도록 기다린다 (최소 20us).
            time.sleep_us(max(20, int(2 * n * 1000000 / self.freq)))

    def reset(self):
        self.tt.reset_project(True)
        self.wait_clocks(10)   # 동기 리셋이라 리셋 중에 클럭이 필요하다
        self.tt.reset_project(False)
        self.wait_clocks(2)


def main(freqs=(None, 1000, 100000, 1000000, 10000000, 25000000, 50000000), n_random=20):
    """수동 클럭부터 시작해서 주파수를 올려 가며 전체 시험을 돌린다."""
    board = TTBoardAdapter()
    chip = Chip(board)
    table = []
    for f in freqs:
        name = "수동 클럭" if f is None else "%d Hz" % f
        print("=== " + name + " ===")
        try:
            board.set_clock(f)
            r = run_all(chip, n_random=n_random)
            table.append((name, r["passed"], r["total"]))
        except Exception as e:  # done 이 안 오는 경우 등
            print("FAIL  " + name + " 에서 멈춤: " + str(e))
            table.append((name, 0, -1))
    board.set_clock(None)
    print("=== 요약 ===")
    for name, passed, total in table:
        print("%-12s %s" % (name, "멈춤" if total < 0 else "%d / %d" % (passed, total)))
    return table
