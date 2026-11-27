/*
 * Copyright (c) 2026 tiny-ai-chip
 * SPDX-License-Identifier: Apache-2.0
 *
 * systolic_2x2: 비트 직렬 MAC 4개로 만든 2x2 systolic array. C = A x B 를 계산한다.
 *
 * Output stationary 방식: 결과 C[i][j] 는 PE(i,j) 의 acc 에 머물고,
 * A 의 값은 오른쪽으로, B 의 값은 아래로 한 클럭에 한 칸씩 흘러간다.
 *
 *               b_in0                b_in1
 *                 |                    |
 *                 v                    v
 *   a_in0 ---> [ PE00 ] --a_pass0--> [ PE01 ]
 *                 |                    |
 *              b_pass0              b_pass1
 *                 v                    v
 *   a_in1 ---> [ PE10 ] --a_pass1--> [ PE11 ]
 *
 *   a_pass0, a_pass1, b_pass0, b_pass1 은 8비트 레지스터(한 클럭 지연)다.
 *
 * 박자(beat): 각 MAC 은 곱 하나에 en 8 클럭이 걸린다 (mac_serial.v 참고).
 *   한 박자 = en 8 클럭. 그동안 바깥에서 a_in, b_in 을 그대로 둔다.
 *   비트 번호는 각 MAC 이 스스로 센다. 배열도 자기 카운터(beat_pos)로 박자 끝을 알고,
 *   이동 레지스터는 박자의 마지막 클럭(8 번째 en)에만 움직인다.
 *
 * 바깥에서 A 와 B 를 비스듬하게(skew) 넣어야 한다:
 *   박자 t 에 a_in[i] = A[i][t-i], b_in[j] = B[t-j][j]  (범위 밖이면 0)
 * 그러면 4 박자 (32 클럭) 뒤 c00..c11 에 결과가 남는다.
 *
 * 제어 신호: rst_n (리셋), clr (새 계산 시작), en (한 클럭 진행).
 * en = 0 이면 배열 전체가 멈춘다 (acc 도, 이동 레지스터도 그대로).
 */

`default_nettype none

module systolic_2x2 #(
    parameter DATA_W = 8,
    parameter ACC_W  = 18
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     en,
    input  wire                     clr,
    input  wire signed [DATA_W-1:0] a_in0,  // A 의 0번 행이 들어오는 곳 (왼쪽 위)
    input  wire signed [DATA_W-1:0] a_in1,  // A 의 1번 행이 들어오는 곳 (왼쪽 아래)
    input  wire signed [DATA_W-1:0] b_in0,  // B 의 0번 열이 들어오는 곳 (위 왼쪽)
    input  wire signed [DATA_W-1:0] b_in1,  // B 의 1번 열이 들어오는 곳 (위 오른쪽)
    output wire signed [ACC_W-1:0]  c00,
    output wire signed [ACC_W-1:0]  c01,
    output wire signed [ACC_W-1:0]  c10,
    output wire signed [ACC_W-1:0]  c11
);

  // 이웃 PE 로 값을 넘겨주는 이동 레지스터. 오른쪽 끝과 아래쪽 끝은 넘겨줄 곳이 없어서 4개면 된다.
  reg signed [DATA_W-1:0] a_pass0, a_pass1;  // PE00 -> PE01, PE10 -> PE11
  reg signed [DATA_W-1:0] b_pass0, b_pass1;  // PE00 -> PE10, PE01 -> PE11

  // 박자 안에서 몇 번째 클럭인지 (0..7). MAC 안의 카운터와 똑같이 움직이지만, 이동 레지스터
  // 32 개의 enable 만 담당해서 선이 덜 퍼진다. keep: 합성 도구가 MAC 카운터와 합치지 못하게.
  (* keep *) reg [2:0] beat_pos;

  always @(posedge clk) begin
    if (!rst_n || clr)
      beat_pos <= 3'd0;
    else if (en)
      beat_pos <= beat_pos + 3'd1;
  end

  wire beat_end = en && (&beat_pos);  // 박자의 마지막 클럭 (beat_pos = 7)

  always @(posedge clk) begin
    if (!rst_n || clr) begin
      a_pass0 <= {DATA_W{1'b0}};
      a_pass1 <= {DATA_W{1'b0}};
      b_pass0 <= {DATA_W{1'b0}};
      b_pass1 <= {DATA_W{1'b0}};
    end else if (beat_end) begin
      a_pass0 <= a_in0;
      a_pass1 <= a_in1;
      b_pass0 <= b_in0;
      b_pass1 <= b_in1;
    end
  end

  mac_serial #(.DATA_W(DATA_W), .ACC_W(ACC_W)) pe00 (
      .clk(clk), .rst_n(rst_n), .en(en), .clr(clr),
      .a(a_in0), .b(b_in0), .acc(c00)
  );

  mac_serial #(.DATA_W(DATA_W), .ACC_W(ACC_W)) pe01 (
      .clk(clk), .rst_n(rst_n), .en(en), .clr(clr),
      .a(a_pass0), .b(b_in1), .acc(c01)
  );

  mac_serial #(.DATA_W(DATA_W), .ACC_W(ACC_W)) pe10 (
      .clk(clk), .rst_n(rst_n), .en(en), .clr(clr),
      .a(a_in1), .b(b_pass0), .acc(c10)
  );

  mac_serial #(.DATA_W(DATA_W), .ACC_W(ACC_W)) pe11 (
      .clk(clk), .rst_n(rst_n), .en(en), .clr(clr),
      .a(a_pass1), .b(b_pass1), .acc(c11)
  );

endmodule
