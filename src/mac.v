/*
 * Copyright (c) 2026 tiny-ai-chip
 * SPDX-License-Identifier: Apache-2.0
 *
 * mac: 곱하고 누적하기 (Multiply-ACcumulate).
 *
 *   a (8비트) ──┐
 *               ├──[ 곱셈기 ]── product (16비트) ──┐
 *   b (8비트) ──┘                                  │
 *                                          ┌──[ 덧셈기 ]──[ acc 레지스터 (18비트) ]──┬── acc
 *                                          │                                          │
 *                                          └──────────────────────────────────────────┘
 *
 * 매 클럭(올라가는 엣지)마다 우선순위대로 하나만 한다:
 *   1. rst_n = 0 이면 acc = 0 (리셋)
 *   2. clr   = 1 이면 acc = 0 (새 계산 시작)
 *   3. en    = 1 이면 acc = acc + a * b
 *   4. 그 외에는 acc 를 그대로 둔다.
 *
 * a, b, acc 는 모두 부호 있는 2의 보수 정수다. AI 칩이 쓰는 int8 형식과 같다.
 */

`default_nettype none

module mac #(
    parameter DATA_W = 8,   // 입력 a, b 의 비트폭
    parameter ACC_W  = 18   // 누적값 acc 의 비트폭: 곱 16비트 + 여유 2비트 (곱 4개까지 안전)
) (
    input  wire                     clk,
    input  wire                     rst_n,  // 0 이면 리셋 (active low)
    input  wire                     en,     // 1 이면 누적
    input  wire                     clr,    // 1 이면 acc 를 0 으로
    input  wire signed [DATA_W-1:0] a,
    input  wire signed [DATA_W-1:0] b,
    output reg  signed [ACC_W-1:0]  acc
);

  // 8비트 x 8비트 = 16비트. 두 입력이 signed 라서 부호 있는 곱셈이 된다.
  wire signed [2*DATA_W-1:0] product = a * b;

  // 16비트 곱을 18비트로 늘린다. 맨 위 비트(부호)를 복사해서 채워야 음수가 그대로 음수로 남는다.
  //   예: -12 = 1111_1111_1111_0100 (16비트) -> 11_1111_1111_1111_0100 (18비트)
  wire signed [ACC_W-1:0] product_ext = {{(ACC_W - 2*DATA_W){product[2*DATA_W-1]}}, product};

  always @(posedge clk) begin
    if (!rst_n)
      acc <= {ACC_W{1'b0}};
    else if (clr)
      acc <= {ACC_W{1'b0}};
    else if (en)
      acc <= acc + product_ext;
  end

endmodule
