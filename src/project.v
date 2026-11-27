/*
 * Copyright (c) 2026 jameshfj01-maker
 * SPDX-License-Identifier: Apache-2.0
 *
 * tt_um_jameshfj01_tiny_ai_chip: Tiny Tapeout 최상위 모듈.
 * 핀 8개짜리 버스로 2x2 int8 행렬 A, B 를 써 넣고, C = A x B 를 계산해서 읽어 간다.
 *
 *   ui_in[7:0] ──► 쓰기 데이터 ──┐
 *   uio_in[3:0] ─► 주소 ─────────┼──► [ 저장 레지스터 8바이트: A00..A11, B00..B11 ]
 *   uio_in[4] ──► write ─[동기화]┘                │
 *                                                 v
 *   uio_in[5] ──► start ─[동기화]──► [ 지휘자(상태 기계) ] ──► 비스듬히 밀어 넣기
 *                                                 │                 │
 *   uio_out[7] ◄── done ◄─────────────────────────┘                 v
 *                                       [ systolic_2x2 (완전 비트 직렬 MAC 4개) ]
 *                                                                   │
 *   uo_out[7:0] ◄── 주소로 고른 결과 바이트 ◄── [ 읽기 선택기 ] ◄────┘
 *
 * 쓰기 주소 : 0..3 = A00 A01 A10 A11, 4..7 = B00 B01 B10 B11 (8..15 는 무시)
 * 읽기 주소 : {칸 번호 2비트, 바이트 번호 2비트}
 *             칸 0..3 = C00 C01 C10 C11
 *             바이트 0 = [7:0], 1 = [15:8], 2 = [16] 을 부호 확장, 3 = 0
 *
 * write, start 는 칩 바깥에서 클럭과 상관없이 바뀌는 신호라서 플립플롭 2개로
 * 동기화한 뒤, 0 -> 1 로 바뀌는 순간(상승 엣지)에 한 번만 동작한다.
 * 계산 중(busy)에는 write 와 start 를 무시한다.
 *
 * 계산 시간: 4 박자 x 136 클럭 = 544 클럭 (완전 비트 직렬 MAC 이 곱 하나에 8 줄 x 17 비트를 쓴다).
 * 50MHz 에서 약 11 마이크로초.
 */

`default_nettype none

module tt_um_jameshfj01_tiny_ai_chip (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  localparam ACC_W = 17;

  wire [3:0] addr  = uio_in[3:0];
  wire       write = uio_in[4];
  wire       start = uio_in[5];

  // ---------------------------------------------------------------
  // 1. write, start 동기화 + 상승 엣지 검출
  //    sync[0] -> sync[1] 이 2단 동기화, sync[2] 는 한 클럭 전 값.
  // ---------------------------------------------------------------
  reg [2:0] write_sync, start_sync;

  always @(posedge clk) begin
    if (!rst_n) begin
      write_sync <= 3'b000;
      start_sync <= 3'b000;
    end else begin
      write_sync <= {write_sync[1:0], write};
      start_sync <= {start_sync[1:0], start};
    end
  end

  wire write_rise = write_sync[1] & ~write_sync[2];
  wire start_rise = start_sync[1] & ~start_sync[2];

  // ---------------------------------------------------------------
  // 2. 지휘자: start 가 오면 한 클럭 clr, 그다음 4 박자 동안 en
  //
  //    박자 안의 클럭은 배열 안의 순서 지휘자가 센다. 여기서는 배열이 알려 주는
  //    beat_end (박자의 마지막 클럭) 로 박자 번호 t (0..3) 만 센다.
  // ---------------------------------------------------------------
  reg       busy;
  reg       done;
  reg [1:0] t;  // 박자 번호
  wire      beat_end;

  wire go = start_rise & ~busy;

  always @(posedge clk) begin
    if (!rst_n) begin
      busy <= 1'b0;
      done <= 1'b0;
      t    <= 2'd0;
    end else if (go) begin
      busy <= 1'b1;
      done <= 1'b0;
      t    <= 2'd0;
    end else if (busy && beat_end) begin
      t <= t + 2'd1;
      if (t == 2'd3) begin
        busy <= 1'b0;
        done <= 1'b1;
      end
    end
  end

  // ---------------------------------------------------------------
  // 3. 저장 레지스터: A, B 8바이트
  // ---------------------------------------------------------------
  reg signed [7:0] a00, a01, a10, a11;
  reg signed [7:0] b00, b01, b10, b11;

  always @(posedge clk) begin
    if (!rst_n) begin
      a00 <= 8'sd0; a01 <= 8'sd0; a10 <= 8'sd0; a11 <= 8'sd0;
      b00 <= 8'sd0; b01 <= 8'sd0; b10 <= 8'sd0; b11 <= 8'sd0;
    end else if (write_rise && !busy) begin
      case (addr)
        4'd0: a00 <= ui_in;
        4'd1: a01 <= ui_in;
        4'd2: a10 <= ui_in;
        4'd3: a11 <= ui_in;
        4'd4: b00 <= ui_in;
        4'd5: b01 <= ui_in;
        4'd6: b10 <= ui_in;
        4'd7: b11 <= ui_in;
        default: ;  // 8..15 는 무시
      endcase
    end
  end

  // ---------------------------------------------------------------
  // 4. 비스듬히 밀어 넣기: 박자 t 에 a_in[i] = A[i][t-i], b_in[j] = B[t-j][j]
  //    (한 박자 8 클럭 동안 같은 값을 유지한다)
  //
  //    t:      0     1     2     3
  //    a_in0: A00   A01    0     0
  //    a_in1:  0    A10   A11    0
  //    b_in0: B00   B10    0     0
  //    b_in1:  0    B01   B11    0
  // ---------------------------------------------------------------
  wire signed [7:0] a_in0 = (t == 2'd0) ? a00 : (t == 2'd1) ? a01 : 8'sd0;
  wire signed [7:0] a_in1 = (t == 2'd1) ? a10 : (t == 2'd2) ? a11 : 8'sd0;
  wire signed [7:0] b_in0 = (t == 2'd0) ? b00 : (t == 2'd1) ? b10 : 8'sd0;
  wire signed [7:0] b_in1 = (t == 2'd1) ? b01 : (t == 2'd2) ? b11 : 8'sd0;

  wire signed [ACC_W-1:0] c00, c01, c10, c11;

  systolic_2x2 #(.DATA_W(8), .ACC_W(ACC_W)) array (
      .clk  (clk),
      .rst_n(rst_n),
      .en   (busy),
      .clr  (go),
      .a_in0(a_in0),
      .a_in1(a_in1),
      .b_in0(b_in0),
      .b_in1(b_in1),
      .beat_end(beat_end),
      .c00  (c00),
      .c01  (c01),
      .c10  (c10),
      .c11  (c11)
  );

  // ---------------------------------------------------------------
  // 5. 읽기 선택기: 주소 {칸, 바이트} 로 결과 한 바이트를 고른다
  // ---------------------------------------------------------------
  reg signed [ACC_W-1:0] sel_c;
  always @(*) begin
    case (addr[3:2])
      2'd0: sel_c = c00;
      2'd1: sel_c = c01;
      2'd2: sel_c = c10;
      default: sel_c = c11;
    endcase
  end

  reg [7:0] read_byte;
  always @(*) begin
    case (addr[1:0])
      2'd0: read_byte = sel_c[7:0];
      2'd1: read_byte = sel_c[15:8];
      2'd2: read_byte = {{7{sel_c[16]}}, sel_c[16]};
      default: read_byte = 8'd0;
    endcase
  end

  assign uo_out  = read_byte;
  assign uio_out = {done, 7'b0};
  assign uio_oe  = 8'b1000_0000;  // uio[7] 만 출력 (done), 나머지는 입력

  // 쓰지 않는 입력 (경고 방지)
  wire _unused = &{ena, uio_in[7:6], 1'b0};

endmodule
