/*
 * Copyright (c) 2026 jameshfj01-maker
 * SPDX-License-Identifier: Apache-2.0
 *
 * mac_bitserial: 완전 비트 직렬 MAC. 덧셈기가 1비트 전가산기 하나뿐이다.
 *
 * acc 는 18비트 시프트 레지스터다. 매 클럭 맨 아래 비트 acc[0] 에 "더할 비트" 와 올림수를
 * 더해서, 합 비트를 맨 위로 넣고 오른쪽으로 한 칸 민다. 18 클럭 (한 바퀴) 이 지나면 acc 는
 * 다시 제자리에 오고, 그 바퀴 동안 더한 18비트 수가 acc 에 더해져 있다.
 *
 *          ┌──────────────────── acc (18비트, 오른쪽으로 민다) ────────────────┐
 *   합 ──► │ b17  b16  ...  b1  b0 │ ──► acc[0] ──┐
 *   ▲      └──────────────────────┘                v
 *   │                                     [ 1비트 전가산기 ] ◄── 더할 비트 t
 *   └─────────────── 합 ◄────────────────────┤     ▲
 *                                         올림수 ──► [carry 플립플롭]
 *
 * 한 바퀴에 더하는 수 = 세로 곱셈의 한 줄 = b[i] ? (a << i) : 0.
 * 그 수의 j 번째 비트는 순서 지휘자(bitserial_seq)가 알려 준다:
 *   a_zero = 1 이면 0, 아니면 a[a_idx] (a_idx 는 7 에서 멈춰서 부호 비트가 반복된다).
 * 부호 비트 줄 (neg = 1) 은 빼기라서 2의 보수로 더한다: 비트를 모두 뒤집고 (t ^ neg),
 * 첫 비트에서 올림수 1 로 시작한다 (+1).
 *
 * rst_n = 0 이나 clr = 1 이면 acc = 0, 올림수 = 0. en = 0 이면 멈춘다.
 * (올림수는 바퀴의 첫 비트에서 cin 으로 쓰이지 않으므로, 결과를 두고 새로 시작할 때 따로 지울 필요가 없다.)
 */

`default_nettype none

module mac_bitserial #(
    parameter ACC_W = 18
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    en,
    input  wire                    clr,
    input  wire signed [7:0]       a,
    input  wire signed [7:0]       b,
    input  wire [2:0]              a_idx,   // 아래는 순서 지휘자가 주는 신호
    input  wire                    a_zero,
    input  wire [2:0]              b_idx,
    input  wire                    neg,
    input  wire                    first,
    output reg  signed [ACC_W-1:0] acc
);

  reg carry;

  wire b_bit = b[b_idx];                    // 이번 줄을 더하나?
  wire a_bit = a_zero ? 1'b0 : a[a_idx];    // a << i 의 j 번째 비트
  wire t     = b_bit & (a_bit ^ neg);       // 더할 비트 (빼기 줄이면 뒤집는다)
  wire cin   = first ? (b_bit & neg) : carry;  // 바퀴의 첫 비트: 빼기면 +1 로 시작

  wire s    = acc[0] ^ t ^ cin;                          // 합
  wire cout = (acc[0] & t) | (acc[0] & cin) | (t & cin);  // 올림수

  always @(posedge clk) begin
    if (!rst_n || clr) begin
      acc   <= {ACC_W{1'b0}};
      carry <= 1'b0;
    end else if (en) begin
      acc   <= {s, acc[ACC_W-1:1]};
      carry <= cout;
    end
  end

endmodule
