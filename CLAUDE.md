# tiny-ai-chip

8비트 2x2 systolic array(작은 AI 가속기)를 Tiny Tapeout으로 설계하는 프로젝트.

## 나에 대해

- 고등학생, 디지털 회로 설계는 처음.
- 예전에 Tiny Tapeout을 시도했다가 뭔지 잘 모르고 비용 때문에 그만둔 적이 있다 (그때 저장소: `power-aware-counter`).
- 이번에는 무료 단계(설계, 테스트, 하드닝)를 먼저 끝내고, 제출(유료) 여부는 나중에 결정한다.
- 각 단계가 실제 칩 제조에서 무슨 의미인지 같이 배우고 싶다.

## Claude의 역할: 만드는 사람 겸 설명하는 사람

공부는 따로 한다. 이 저장소에서 만드는 일(설계, 테스트, 커밋, 푸시)은 Claude가 혼자 진행한다.

- 새 개념이 나오면 쉬운 설명과 ASCII 회로도로 보여준다.
- 모듈 하나를 끝낼 때마다 무엇을 만들었고 왜 그렇게 만들었는지 설명한다. 퀴즈나 이해 확인 질문은 하지 않는다.
- 나에게는 의견이나 아이디어가 필요한 설계 선택만 물어본다. 묻지 않은 부분은 Claude가 합리적인 기본값으로 정하고, 무엇을 골랐는지 알려준다.
- 돈이 드는 결정(타일 크기, 제출 여부)은 Claude가 혼자 정하지 않고 나에게 묻는다.
- 각 단계(RTL, 시뮬레이션, 합성, 하드닝, GDS, 제출)가 실제 칩 공장에서 무슨 의미인지 연결해서 설명한다.

## 규칙

1. Claude가 만들고 커밋한다. 커밋 메시지에 무엇을 왜 바꿨는지 쉬운 말로 남기고, 커밋한 내용은 채팅에서도 설명한다.
2. 모든 모듈은 cocotb 테스트를 먼저 쓰고, 그 다음 Verilog를 써서 테스트를 통과시킨다 (테스트 먼저).
3. 엠대시(긴 줄표)는 쓰지 않는다. 코드, 주석, 문서, 커밋 메시지 모두.
4. 폐기조건: 2027년 1월 31일까지 (a) MAC 유닛 테스트 통과 와 (b) GDS 하드닝 성공 이 둘 다 없으면, 칩 제출 목표를 버리고 시뮬레이션 프로젝트로 줄인다. 날짜가 가까워지면 Claude가 먼저 상기시킨다.

## 로드맵

| 단계 | 내용 | 끝났다는 기준 |
|---|---|---|
| 0 | 환경 세팅 | 로컬에서 템플릿 기본 테스트 통과 (완료: 2026-11-26) |
| 1 | MAC 유닛 (곱하고 누적하기) | `mac` 모듈 cocotb 테스트 통과, Claude가 설명 완료 (완료: 2026-11-26) |
| 2 | 2x2 systolic array | MAC 4개를 연결, 2x2 행렬곱 결과를 테스트로 확인 (완료: 2026-11-26) |
| 3 | Tiny Tapeout 래퍼 + 하드닝 | `tt_um_` 최상위 모듈, GitHub Actions의 gds / precheck / gl_test 통과 |
| 4 | 제출 결정 | 비용과 셔틀 일정을 보고 제출할지 결정 (유료 단계) |

## 저장소 정보 (템플릿에서 확인한 사실)

- 템플릿: `TinyTapeout/ttsky-verilog-template` (SKY130 셔틀, ChipFoundry 제조).
- PDK: `sky130A`, 표준 셀 라이브러리 `sky130_fd_sc_hd`.
- 하드닝 도구: LibreLane. GitHub Actions `TinyTapeout/tt-gds-action@ttsky26d`가 push할 때마다 돌린다.
- 기본 클럭: `src/config.json`의 `CLOCK_PERIOD` 20ns (50MHz). 바꾸기 전에 꼭 이유를 이해할 것.
- 타일: `info.yaml`의 `tiles` 기본 "1x1" (약 167x108 um). 2x2 array가 안 들어가면 더 큰 타일이 필요하고, 타일이 클수록 제출 비용이 올라간다.
- 핀 제한: 입력 8개(`ui_in`), 출력 8개(`uo_out`), 양방향 8개(`uio_*`). 8비트 데이터를 어떻게 넣고 뺄지 설계할 때 이 제한이 핵심 제약이다.
- 최상위 모듈 이름은 `tt_um_`으로 시작해야 하고, 바꾸면 `info.yaml`, `test/tb.v`도 같이 바꾼다.
- 현재 최상위 모듈: `tt_um_jameshfj01_tiny_ai_chip` (`src/project.v`). 핀 사용법은 `docs/info.md`에 있다.
- 새 소스 파일을 추가하면 `info.yaml`의 `source_files`와 `test/Makefile`의 `PROJECT_SOURCES` 둘 다 업데이트한다.

## 개발 환경 (클라우드)

GitHub와 Claude Code 클라우드 세션만 쓴다. 컨테이너는 세션이 끝나면 사라지므로 새 세션마다 아래 설치를 다시 한다.

- 시뮬레이터: Icarus Verilog 12.0 (Ubuntu 24.04 `apt` 패키지). GitHub Actions `test` 워크플로도 같은 방식으로 설치한다.
- 린터: Verilator (`apt` 패키지). 하드닝(gds)은 Verilator 경고가 하나라도 있으면 멈추므로, 푸시 전에 꼭 린트를 돌린다.
- Python: 프로젝트 안 `.venv` (Python 3.12, uv로 생성). cocotb 2.1.0, pytest 8.4.2.
- 하드닝(LibreLane)은 설치하지 않고 GitHub Actions로 돌린다.

### 설치

```bash
sudo apt-get update && sudo apt-get install -y iverilog verilator
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r test/requirements.txt
```

### 테스트 실행

최상위 모듈 테스트:

```bash
cd test
source ../.venv/bin/activate
make -B
python -m cocotb_tools.check_results results.xml
```

모듈 단위 테스트 (`test/mac`, `test/systolic` 각각):

```bash
cd test/mac          # 또는 test/systolic
source ../../.venv/bin/activate
make -B
python -m cocotb_tools.check_results results.xml
```

새 모듈 테스트 폴더를 만들면 `.github/workflows/test.yaml`의 "Run module unit tests" 목록에도 추가한다.

`make`는 테스트가 실패해도 성공으로 끝날 수 있어서 마지막 줄로 결과를 꼭 확인한다.

### 린트 (푸시 전에)

```bash
verilator --lint-only -Wall -Wno-DECLFILENAME --top-module tt_um_jameshfj01_tiny_ai_chip \
  src/mac.v src/systolic_2x2.v src/project.v
```

새 소스 파일을 추가하면 이 명령과 `.github/workflows/test.yaml`의 "Lint with Verilator" 단계에도 추가한다.
