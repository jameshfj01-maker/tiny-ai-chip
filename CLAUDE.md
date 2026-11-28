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
4. 폐기조건: 2027년 1월 31일까지 (a) MAC 유닛 테스트 통과 와 (b) GDS 하드닝 성공 이 둘 다 없으면, 칩 제출 목표를 버리고 시뮬레이션 프로젝트로 줄인다. 날짜가 가까워지면 Claude가 먼저 상기시킨다. (2026-11-27 현재: (a) 2026-11-26 충족, (b) 2026-11-27 2x2 타일로 충족. 칩 제출 목표 유지.)

## 로드맵

| 단계 | 내용 | 끝났다는 기준 |
|---|---|---|
| 0 | 환경 세팅 | 로컬에서 템플릿 기본 테스트 통과 (완료: 2026-11-26) |
| 1 | MAC 유닛 (곱하고 누적하기) | `mac` 모듈 cocotb 테스트 통과, Claude가 설명 완료 (완료: 2026-11-26) |
| 2 | 2x2 systolic array | MAC 4개를 연결, 2x2 행렬곱 결과를 테스트로 확인 (완료: 2026-11-26) |
| 3 | Tiny Tapeout 래퍼 + 하드닝 | `tt_um_` 최상위 모듈, GitHub Actions의 gds / precheck / gl_test 통과 (완료: 2026-11-27, 2x2 타일) |
| 4 | 제출 결정 | 비용과 셔틀 일정을 보고 제출할지 결정 (유료 단계). 2026-11-27 결정: TTSKY26d/e (마감 2026-11-30) 는 건너뛰고 다음 셔틀을 기다린다. 2026-11-27 결정: 제출은 1x1 타일 (완전 비트 직렬 버전) 로 한다. 기준 커밋 5159fc3 (2026-11-28, 더하기 모드 포함) |

### 다음 셔틀이 열리면 할 일

1. Tiny Tapeout 사이트 (tinytapeout.com/chips) 에서 새 SKY130 셔틀 이름, 마감일, 칩 도착 예정일을 확인한다.
2. 새 셔틀용 템플릿에서 바뀐 점을 확인하고 맞춘다: `.github/workflows/*.yaml` 의 `tt-gds-action@ttsky26d` 태그, `info.yaml` 의 `yaml_version`, `src/config.json`.
3. 하드닝을 다시 돌려서 gds / precheck / gl_test 통과와 타이밍 (모든 코너 setup 여유가 양수인지) 을 확인한다.
4. 사용자가 계산기 (app.tinytapeout.com/calculator) 로 1x1 (1타일) 가격과 칩/보드 가격을 확인하고, 제출 여부를 정한다. 결제와 제출은 사용자가 직접 한다.

### 타일 결정 기록

- 2026-11-26: 1x1 타일에서 하드닝 결과 사용률 209.6% (표준 셀 2,697개, 약 29,200 um²). 곱셈기 4개가 대부분을 차지한다.
- 결정: 먼저 `tiles: "2x2"`로 하드닝 성공을 확인한다 (하드닝은 무료, 비용은 제출할 때만 든다). 제출 전에 MAC 곱셈기를 비트 직렬(한 클럭에 1비트씩, 8클럭)로 바꿔서 1x2 또는 1x1로 줄이는 것을 시도한다.
- 2026-11-27: 2x2 타일로 gds / precheck / gl_test 통과. DRC, LVS 오류 없음, hold 위반 없음.
  단, 가장 느린 조건(ss, 100도, 1.60V) 3개 코너에서 50MHz setup 위반 경고가 있다. 원인은 8비트 곱셈 + 18비트 덧셈이 한 클럭 안에 있는 긴 경로로 보인다.
  비트 직렬 MAC으로 바꾸면 이 긴 경로가 없어지므로, 바꾼 뒤 타이밍을 다시 확인한다.
- 2026-11-27: 비트 직렬 MAC (`src/mac_serial.v`) 으로 교체. 곱 하나에 8클럭, 행렬곱 한 번에 32클럭.
  Yosys 일반 게이트 기준 2,813개에서 1,196개로 줄었다 (논리 게이트 2,635개에서 1,015개, 플립플롭은 약 180개로 그대로).
  추정 면적 약 14,700 um²: 1x1 (약 16,500 um²) 은 너무 빠듯하고, 1x2 (약 34,000 um²) 는 여유가 있다. 그래서 `tiles: "1x2"`로 하드닝을 시도한다.
  병렬 버전 `src/mac.v`와 `test/mac`은 비교용으로 남기고 칩 소스에서는 뺐다.
- 2026-11-27: 비트 직렬 버전을 1x2 타일로 하드닝. gds / precheck / gl_test 통과, DRC, LVS 오류 없음, hold 위반 없음.
  실제 면적: 논리 셀 약 10,900 um² + 플립플롭 181개 약 3,850 um² (합 약 14,700 um², 추정과 같음).
  버퍼, 탭 셀까지 합친 표준 셀 면적 19,411 um², 코어 34,255 um², 사용률 56.7%.
  setup 여유 (20ns 클럭 기준): 보통 조건 nom_tt +7.20ns, 느린 조건 nom_ss +0.30ns, min_ss +0.62ns, max_ss -0.04ns (경로 1개).
  병렬 2x2 때는 ss 코너 3개 모두 위반이었고 지금은 가장 나쁜 1개만 40ps 모자란다.
  가장 느린 경로: 지휘자 카운터의 bit_idx 가 MAC 4개의 자리 옮기기 회로로 퍼지는 선 (연결이 많아서 버퍼가 줄줄이 붙음) 에서 시작해 18비트 덧셈기를 지나 acc 로 간다.
  같은 이유로 max slew (신호가 너무 천천히 바뀜) 경고도 있다: max_ss 535개, nom_tt 22개.
  1x1 에 넣으려면 사용률 60% 기준 논리 + 플립플롭이 약 9,900 um² 이하여야 해서 지금보다 약 1/3 을 더 줄여야 한다.
- 2026-11-27: 위 느린 경로를 고침. 가장 느린 경로 20.04ns 중 약 8ns 가 공유 bit_idx 선의 팬아웃 버퍼 6개에서 쓰였다.
  각 MAC 이 자기 3비트 카운터를 갖도록 바꿨다 (배열도 박자 끝을 알려고 자기 카운터를 하나 가진다). `(* keep *)` 로 합성 도구가 카운터들을 하나로 합치지 못하게 했다.
  Yosys 기준 플립플롭 181개에서 196개 (카운터 5개 x 3비트), 논리 게이트 1,015개에서 1,044개.
- 2026-11-27: 고친 버전 1x2 하드닝 결과. gds / precheck / gl_test 통과, DRC, LVS, 안테나 오류 없음.
  setup 여유: max_ss +1.71ns, nom_ss +1.92ns, min_ss +2.13ns, nom_tt +6.67ns. setup 위반 0, hold 위반 0. 50MHz 를 모든 코너에서 만족한다.
  max slew 경고: nom_tt 22개에서 0개, max_ss 535개에서 481개 (가장 나쁜 코너에만 남음).
  사용률 58.5% (표준 셀 20,026 um², 플립플롭 196개). 지금 가장 느린 경로는 칩 바깥 핀(uio_in 주소)에서 읽기 선택기를 지나 uo_out 핀으로 가는 경로다.
  결론: 제출 후보는 이 설계와 1x2 타일 (2타일).
- 2026-11-27: 사용자 요청으로 1x1 타일에 넣기 시도. MAC 을 완전 비트 직렬 (`src/mac_bitserial.v`) 로 바꿨다.
  acc 17비트 시프트 레지스터 + 1비트 전가산기 1개 + 올림수 플립플롭. 한 바퀴(17클럭)에 세로 곱셈 한 줄, 곱 하나에 136클럭, 행렬곱 한 번에 544클럭 (50MHz 에서 약 11us).
  비트 순서는 공유 순서 지휘자 `src/bitserial_seq.v` 하나가 정한다 (경로가 짧아서 팬아웃 문제가 다시 생기지 않을 것으로 봄).
  acc 는 18비트에서 17비트로 줄였다 (2x2 의 한 칸은 곱 2개의 합: -32512 ~ 32768).
  Yosys 일반 게이트: 1,240개에서 670개 (논리 1,044개에서 484개, 플립플롭 196개에서 186개). 이전 하드닝 비율로 추정한 면적 약 9,200 um².
  1x1 에서는 배치 단계가 핀 수에 따른 여유 면적을 더하므로, 기본 목표 밀도 60% 를 넘을 수 있다. 첫 하드닝 결과를 보고 `src/config.json` 의 `PL_TARGET_DENSITY_PCT` 를 올릴지 정한다.
  병렬 버전 `src/mac_serial.v` 와 `test/mac_serial` 은 비교용으로 남기고 칩 소스에서는 뺐다. 1x2 버전은 커밋 c011723 에 있다.
- 2026-11-27: 완전 비트 직렬 버전 1x1 하드닝 성공 (설정 변경 없이 기본 목표 밀도 60% 로 통과). gds / precheck / gl_test 통과, DRC, LVS, 안테나 오류 없음.
  표준 셀 면적 13,240 um² (논리 5,582 + 플립플롭 186개 3,956 + 타이밍 버퍼 2,285 + 클럭 버퍼 1,091 등), 코어 16,493 um², 사용률 80.3%.
  setup 여유: max_ss +3.56ns, nom_ss +3.73ns, min_ss +3.92ns, nom_tt +7.63ns (1x2 때보다 더 좋다). setup 위반 0, hold 위반 0.
  max slew 경고: max_ss 481개에서 286개, nom_tt 0개. 가장 느린 경로는 여전히 핀(uio_in 주소) 에서 읽기 선택기를 지나 uo_out 핀으로 가는 경로다.
  결론: 제출 후보는 이 설계와 1x1 타일 (1타일, 1x2 의 절반 비용). 대가는 계산 시간 (36 클럭에서 548 클럭, 50MHz 에서 약 11us). 1x2 버전은 커밋 c011723.
- 2026-11-27 결정 (사용자): 제출은 1x1 타일, 완전 비트 직렬 버전으로 한다. 기준 커밋은 5344e8e (그 뒤에 기록만 바꾼 커밋은 회로와 같다). 2026-11-28 에 더하기 모드를 넣으면서 기준 커밋을 5159fc3 로 옮겼다 (아래).
  다음 셔틀에서 다시 하드닝할 때도 `info.yaml` 의 `tiles: "1x1"` 을 유지한다. 1x2 버전 (커밋 c011723) 은 되돌아갈 때만 쓴다.
- 2026-11-28: 사용자 요청으로 큰 행렬 계산 모드 추가. `uio[6]` = ACC 핀: start 할 때 1 이면 결과를 지우지 않고 더한다 (C = C + A x B).
  4x4 행렬곱 = 2x2 블록으로 나눠, 결과 블록마다 보통 start 1 번 + 더하기 start 1 번 (모두 8 번). 데모 보드 스크립트 `Chip.matmul4` 가 이렇게 한다.
  acc 를 17비트에서 18비트로 늘렸다: 4x4 의 한 칸은 곱 4 개의 합이라 끝값 (-128)x(-128)x4 = 65536 은 17비트에 안 들어간다. 18비트면 4x4 까지 항상 정확하고, 더 큰 행렬은 끝값이 많으면 넘칠 수 있다.
  배열에 `restart` 입력 추가 (순서 지휘자와 이동 레지스터만 처음으로, 결과는 그대로). 계산 시간 576 클럭 (start 부터 done 까지 약 580).
  Yosys 일반 게이트 670개에서 687개 (플립플롭 186개에서 190개).
- 2026-11-28: 더하기 모드 버전 1x1 하드닝 성공 (커밋 5159fc3). gds / precheck / gl_test 통과, DRC, LVS, 안테나 오류 없음.
  표준 셀 면적 14,084 um² (논리 5,738 + 플립플롭 190개 4,041 + 타이밍 버퍼 2,913 + 클럭 버퍼 1,061 등), 사용률 85.4% (예상 81~82% 보다 높음, 타이밍 버퍼가 628 um² 늘었다).
  setup 여유: max_ss +3.38ns, nom_ss +3.59ns, min_ss +3.84ns, nom_tt +7.54ns. setup 위반 0, hold 위반 0. max slew 경고 max_ss 286개에서 368개, nom_tt 0개.
  1x1 결정은 그대로이고, 제출 기준 커밋은 5344e8e 에서 5159fc3 (더하기 모드 포함) 으로 바뀐다. 사용률이 85% 라 다음에 기능을 더 넣으면 1x1 에 안 들어갈 수 있다.
- `viewer` 작업은 GitHub Pages가 꺼져 있어서 실패한다. 칩 3D 미리보기용이고 제출에는 필요 없다. 켜려면 저장소 Settings, Pages, Source를 "GitHub Actions"로 바꾼다.

## 저장소 정보 (템플릿에서 확인한 사실)

- 템플릿: `TinyTapeout/ttsky-verilog-template` (SKY130 셔틀, ChipFoundry 제조).
- PDK: `sky130A`, 표준 셀 라이브러리 `sky130_fd_sc_hd`.
- 하드닝 도구: LibreLane. GitHub Actions `TinyTapeout/tt-gds-action@ttsky26d`가 push할 때마다 돌린다.
- 기본 클럭: `src/config.json`의 `CLOCK_PERIOD` 20ns (50MHz). 바꾸기 전에 꼭 이유를 이해할 것.
- 타일: `info.yaml`의 `tiles` 기본 "1x1" (약 167x108 um). 2x2 array가 안 들어가면 더 큰 타일이 필요하고, 타일이 클수록 제출 비용이 올라간다.
- 핀 제한: 입력 8개(`ui_in`), 출력 8개(`uo_out`), 양방향 8개(`uio_*`). 8비트 데이터를 어떻게 넣고 뺄지 설계할 때 이 제한이 핵심 제약이다.
- 최상위 모듈 이름은 `tt_um_`으로 시작해야 하고, 바꾸면 `info.yaml`, `test/tb.v`도 같이 바꾼다.
- 현재 최상위 모듈: `tt_um_jameshfj01_tiny_ai_chip` (`src/project.v`). 핀 사용법은 `docs/info.md`에 있다.
- 핀: `ui_in` 데이터, `uio[3:0]` 주소, `uio[4]` write, `uio[5]` start, `uio[6]` ACC (더하기 모드), `uio[7]` done (칩 출력), `uo_out` 결과 바이트.
- 칩 소스 파일: `src/project.v`, `src/systolic_2x2.v`, `src/bitserial_seq.v`, `src/mac_bitserial.v`. (`src/mac.v`, `src/mac_serial.v`는 참고용, 칩에 안 들어감)
- 프로젝트 정리 문서: `PROJECT_SUMMARY.md` (Claude Docs 의 "Tiny AI Chip 프로젝트 정리" 와 같은 내용). 설계나 결과가 바뀌면 같이 고친다.
- 데모 보드 시험: `demoboard/README.md` (칩이 왔을 때 할 순서), `demoboard/tiny_ai_chip.py` (MicroPython 스크립트). 스크립트는 `test/demoboard`에서 RTL에 연결해 확인한다. 핀 사용법을 바꾸면 이 스크립트도 같이 바꾼다.
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

모듈 단위 테스트 (`test/mac`, `test/mac_serial`, `test/mac_bitserial`, `test/systolic`, `test/demoboard` 각각):

```bash
cd test/mac_bitserial   # 또는 test/mac, test/mac_serial, test/systolic, test/demoboard
source ../../.venv/bin/activate
make -B
python -m cocotb_tools.check_results results.xml
```

새 모듈 테스트 폴더를 만들면 `.github/workflows/test.yaml`의 "Run module unit tests" 목록에도 추가한다.

`make`는 테스트가 실패해도 성공으로 끝날 수 있어서 마지막 줄로 결과를 꼭 확인한다.

### 린트 (푸시 전에)

```bash
verilator --lint-only -Wall -Wno-DECLFILENAME --top-module tt_um_jameshfj01_tiny_ai_chip \
  src/bitserial_seq.v src/mac_bitserial.v src/systolic_2x2.v src/project.v
```

새 소스 파일을 추가하면 이 명령과 `.github/workflows/test.yaml`의 "Lint with Verilator" 단계에도 추가한다.
