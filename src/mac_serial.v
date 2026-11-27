/*
 * Copyright (c) 2026 jameshfj01-maker
 * SPDX-License-Identifier: Apache-2.0
 *
 * mac_serial: 비트 직렬 MAC (곱하고 누적하기).
 *
 * a * b 를 한 번에 곱하지 않고, 손으로 하는 세로 곱셈처럼 b 의 비트 하나씩
 * 8 클럭에 나눠서 더한다. 큰 곱셈기 대신 덧셈기 하나만 있으면 돼서 작다.
 *
 *   a = 13 (0000_1101), b = 11 (0000_1011)
 *
 *   bit_idx 0: b[0] = 1  ->  acc +=  13 << 0  =  13
 *   bit_idx 1: b[1] = 1  ->  acc +=  13 << 1  =  26
 *   bit_idx 2: b[2] = 0  ->  acc +=   0
 *   bit_idx 3: b[3] = 1  ->  acc +=  13 << 3  = 104
 *   ...                                   합계 = 143 = 13 * 11
 *
 *   b 의 맨 위 비트(부호 비트)는 2의 보수에서 무게가 +128 이 아니라 -128 이라서
 *   bit_idx = 7 에서는 더하지 않고 뺀다. 그래서 음수 b 도 맞게 계산된다.
 *
 *          a (8비트) ──► [ << bit_idx ] ──► [ +/- 선택 ] ──┐
 *                          (자리 옮기기)                   v
 *   b[bit_idx] (1비트) ───────────────────► 더할까? ──► [ 덧셈기 18비트 ] ──► [ acc ]
 *                                                          ^                    │
 *                                                          └────────────────────┘
 *
 * bit_idx 는 MAC 안의 3비트 카운터다. en 이 1 일 때마다 0, 1, ..., 7, 0, ... 으로 돈다.
 * 예전에는 바깥 카운터 하나를 MAC 4 개가 같이 썼는데, 그 선 하나가 수백 군데로
 * 퍼지는 바람에 버퍼가 줄줄이 붙어 가장 느린 경로가 됐다 (팬아웃 문제).
 * 그래서 MAC 마다 자기 카운터를 둔다. 플립플롭 3 개만 더 든다.
 *
 * 매 클럭 우선순위: rst_n = 0 -> acc = 0, 카운터 = 0
 *                   clr = 1   -> acc = 0, 카운터 = 0
 *                   en = 1    -> acc = acc + (이번 비트의 값), 카운터 + 1
 *                   그 외 유지.
 */

`default_nettype none

module mac_serial #(
    parameter DATA_W = 8,   // a, b 비트폭
    parameter ACC_W  = 18,  // acc 비트폭 (곱 16비트 + 여유 2비트)
    parameter IDX_W  = 3    // bit_idx 비트폭 (2^3 = 8 = DATA_W)
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     en,
    input  wire                     clr,
    input  wire signed [DATA_W-1:0] a,
    input  wire signed [DATA_W-1:0] b,
    output reg  signed [ACC_W-1:0]  acc
);

  // 이번 클럭에 처리할 b 의 비트 번호.
  // keep: 합성 도구가 "MAC 4 개의 카운터가 똑같다" 며 하나로 합치지 못하게 한다
  // (합치면 다시 선 하나가 4 곳으로 퍼지는 원래 문제로 돌아간다).
  (* keep *) reg [IDX_W-1:0] bit_idx;

  always @(posedge clk) begin
    if (!rst_n || clr)
      bit_idx <= {IDX_W{1'b0}};
    else if (en)
      bit_idx <= bit_idx + 1'b1;  // 7 다음에는 저절로 0 으로 돌아간다 (3비트라서)
  end

  // a 를 부호 유지한 채 18비트로 늘린 다음, bit_idx 만큼 왼쪽으로 민다 (= 2^bit_idx 곱하기).
  wire signed [ACC_W-1:0] a_ext     = {{(ACC_W - DATA_W){a[DATA_W-1]}}, a};
  wire signed [ACC_W-1:0] a_shifted = a_ext <<< bit_idx;

  wire b_bit    = b[bit_idx];                       // 이번에 볼 b 의 비트
  // 부호 비트 번호는 7 = 3'b111 (DATA_W = 2^IDX_W 이므로 bit_idx 가 전부 1 일 때).
  wire sign_bit = &bit_idx;                         // 부호 비트면 빼야 한다

  always @(posedge clk) begin
    if (!rst_n)
      acc <= {ACC_W{1'b0}};
    else if (clr)
      acc <= {ACC_W{1'b0}};
    else if (en && b_bit) begin
      if (sign_bit)
        acc <= acc - a_shifted;
      else
        acc <= acc + a_shifted;
    end
  end

endmodule
