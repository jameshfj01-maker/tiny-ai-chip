/*
 * Copyright (c) 2026 jameshfj01-maker
 * SPDX-License-Identifier: Apache-2.0
 *
 * systolic_2x2: 완전 비트 직렬 MAC 4개로 만든 2x2 systolic array. C = A x B 를 계산한다.
 *
 * Output stationary 방식: 결과 C[i][j] 는 PE(i,j) 의 acc 에 머물고,
 * A 의 값은 오른쪽으로, B 의 값은 아래로 한 박자에 한 칸씩 흘러간다.
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
 *   a_pass0, a_pass1, b_pass0, b_pass1 은 8비트 레지스터(한 박자 지연)다.
 *
 * 박자(beat): 각 MAC 은 곱 하나에 8 줄 x 18 비트 = 144 클럭이 걸린다 (mac_bitserial.v 참고).
 *   한 박자 = en 144 클럭. 그동안 바깥에서 a_in, b_in 을 그대로 둔다.
 *   순서 지휘자(bitserial_seq) 하나가 4 개 MAC 의 비트 순서를 같이 정한다.
 *   이동 레지스터는 박자의 마지막 클럭에만 움직이고, 그 클럭에 beat_end = 1 이다.
 *
 * 바깥에서 A 와 B 를 비스듬하게(skew) 넣어야 한다:
 *   박자 t 에 a_in[i] = A[i][t-i], b_in[j] = B[t-j][j]  (범위 밖이면 0)
 * 그러면 4 박자 (576 클럭) 뒤 c00..c11 에 결과가 남는다.
 *
 * 제어 신호: rst_n (리셋), en (한 클럭 진행), 그리고 새로 시작하는 두 가지:
 *   clr     = 결과(acc) 까지 모두 0 으로 하고 시작. C = A x B.
 *   restart = 순서 지휘자와 이동 레지스터만 처음으로, 결과는 그대로. C = (이전 C) + A x B.
 *             큰 행렬을 2x2 블록으로 나눠 계산할 때 블록 곱을 더해 가는 데 쓴다.
 * en = 0 이면 배열 전체가 멈춘다. c00..c11 은 박자가 끝났을 때만 제자리 값이다.
 */

`default_nettype none

module systolic_2x2 #(
    parameter DATA_W = 8,
    parameter ACC_W  = 18   // 곱 4 개의 합 (4x4 행렬곱의 한 칸): -65024 ~ 65536 이 정확히 들어간다
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     en,
    input  wire                     clr,      // 결과까지 지우고 새로 시작
    input  wire                     restart,  // 결과는 두고 새로 시작 (더하기)
    input  wire signed [DATA_W-1:0] a_in0,  // A 의 0번 행이 들어오는 곳 (왼쪽 위)
    input  wire signed [DATA_W-1:0] a_in1,  // A 의 1번 행이 들어오는 곳 (왼쪽 아래)
    input  wire signed [DATA_W-1:0] b_in0,  // B 의 0번 열이 들어오는 곳 (위 왼쪽)
    input  wire signed [DATA_W-1:0] b_in1,  // B 의 1번 열이 들어오는 곳 (위 오른쪽)
    output wire                     beat_end,  // 박자의 마지막 클럭
    output wire signed [ACC_W-1:0]  c00,
    output wire signed [ACC_W-1:0]  c01,
    output wire signed [ACC_W-1:0]  c10,
    output wire signed [ACC_W-1:0]  c11
);

  // ---------------------------------------------------------------
  // 순서 지휘자: MAC 4 개가 같이 쓴다
  // ---------------------------------------------------------------
  wire [2:0] a_idx, b_idx;
  wire       a_zero, neg, first;

  wire new_start = clr | restart;  // 순서와 이동 레지스터는 둘 다 처음으로

  bitserial_seq #(.ACC_W(ACC_W)) seq (
      .clk(clk), .rst_n(rst_n), .en(en), .clr(new_start),
      .a_idx(a_idx), .a_zero(a_zero), .b_idx(b_idx), .neg(neg), .first(first),
      .last(beat_end)
  );

  // ---------------------------------------------------------------
  // 이동 레지스터: 오른쪽 끝과 아래쪽 끝은 넘겨줄 곳이 없어서 4개면 된다
  // ---------------------------------------------------------------
  reg signed [DATA_W-1:0] a_pass0, a_pass1;  // PE00 -> PE01, PE10 -> PE11
  reg signed [DATA_W-1:0] b_pass0, b_pass1;  // PE00 -> PE10, PE01 -> PE11

  always @(posedge clk) begin
    if (!rst_n || new_start) begin
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

  // ---------------------------------------------------------------
  // MAC 4 개
  // ---------------------------------------------------------------
  mac_bitserial #(.ACC_W(ACC_W)) pe00 (
      .clk(clk), .rst_n(rst_n), .en(en), .clr(clr), .a(a_in0), .b(b_in0),
      .a_idx(a_idx), .a_zero(a_zero), .b_idx(b_idx), .neg(neg), .first(first), .acc(c00)
  );

  mac_bitserial #(.ACC_W(ACC_W)) pe01 (
      .clk(clk), .rst_n(rst_n), .en(en), .clr(clr), .a(a_pass0), .b(b_in1),
      .a_idx(a_idx), .a_zero(a_zero), .b_idx(b_idx), .neg(neg), .first(first), .acc(c01)
  );

  mac_bitserial #(.ACC_W(ACC_W)) pe10 (
      .clk(clk), .rst_n(rst_n), .en(en), .clr(clr), .a(a_in1), .b(b_pass0),
      .a_idx(a_idx), .a_zero(a_zero), .b_idx(b_idx), .neg(neg), .first(first), .acc(c10)
  );

  mac_bitserial #(.ACC_W(ACC_W)) pe11 (
      .clk(clk), .rst_n(rst_n), .en(en), .clr(clr), .a(a_pass1), .b(b_pass1),
      .a_idx(a_idx), .a_zero(a_zero), .b_idx(b_idx), .neg(neg), .first(first), .acc(c11)
  );

endmodule
