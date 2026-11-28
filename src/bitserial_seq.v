/*
 * Copyright (c) 2026 jameshfj01-maker
 * SPDX-License-Identifier: Apache-2.0
 *
 * bitserial_seq: 완전 비트 직렬 MAC 들의 순서 지휘자. 배열에 하나만 두고 MAC 4 개가 같이 쓴다.
 *
 * 곱 a * b 는 세로 곱셈의 줄 8 개 (i = 0..7) 의 합이다. 각 줄은 b[i] ? (a << i) : 0 이고,
 * 부호 비트 줄 (i = 7) 은 빼기다. MAC 은 acc 를 한 비트씩 (j = 0..ACC_W-1) 돌리면서 더하므로
 * 지휘자는 두 카운터를 센다:
 *
 *   j : 지금 acc 의 몇 번째 비트를 더하는지 (0..17)   한 바퀴 = 18 클럭
 *   i : 지금 몇 번째 줄인지 (0..7)                    곱 하나 = 8 바퀴 = 144 클럭
 *
 * 그리고 MAC 들에게 알려 준다 ("a << i" 의 j 번째 비트가 a 의 몇 번째 비트인지):
 *
 *   a_zero : j < i 이면 1 (a << i 의 아래 i 비트는 0)
 *   a_idx  : j - i (7 보다 크면 7. a 는 부호 있는 수라서 위쪽은 부호 비트 a[7] 이 반복된다)
 *   b_idx  : i     (이번 줄의 b 비트)
 *   neg    : i == 7 (빼기 줄)
 *   first  : j == 0 (한 바퀴의 첫 클럭. 올림수를 새로 시작한다)
 *   last   : 곱 하나의 마지막 클럭 (en 이고 i == 7, j == ACC_W-1)
 *
 * rst_n = 0 이나 clr = 1 이면 j = i = 0. en = 1 일 때만 한 칸 나아간다.
 */

`default_nettype none

module bitserial_seq #(
    parameter ACC_W = 18
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    input  wire       clr,
    output wire [2:0] a_idx,
    output wire       a_zero,
    output wire [2:0] b_idx,
    output wire       neg,
    output wire       first,
    output wire       last
);

  reg [4:0] j;
  reg [2:0] i;

  localparam [4:0] J_LAST = ACC_W - 1;

  wire pass_end = (j == J_LAST);  // 한 바퀴의 마지막 비트

  always @(posedge clk) begin
    if (!rst_n || clr) begin
      j <= 5'd0;
      i <= 3'd0;
    end else if (en) begin
      if (pass_end) begin
        j <= 5'd0;
        i <= i + 3'd1;  // 7 다음은 0 (다음 곱의 첫 줄)
      end else begin
        j <= j + 5'd1;
      end
    end
  end

  wire [4:0] i_wide = {2'b00, i};
  wire [4:0] d      = j - i_wide;  // j >= i 일 때만 쓴다

  assign a_zero = (j < i_wide);
  assign a_idx  = (d > 5'd7) ? 3'd7 : d[2:0];
  assign b_idx  = i;
  assign neg    = &i;
  assign first  = (j == 5'd0);
  assign last   = en && neg && pass_end;

endmodule
