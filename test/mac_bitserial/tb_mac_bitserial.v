`default_nettype none
`timescale 1ns / 1ps

// 시험용 묶음: 순서 지휘자(bitserial_seq) 1 개 + 완전 비트 직렬 MAC 1 개.
// 칩 안에서는 지휘자 1 개를 MAC 4 개가 같이 쓴다.
module tb_mac_bitserial (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               en,
    input  wire               clr,
    input  wire signed [7:0]  a,
    input  wire signed [7:0]  b,
    output wire signed [17:0] acc,
    output wire               last   // 곱 하나의 마지막 클럭 (이 클럭이 끝나면 acc 에 곱이 다 더해진다)
);
  wire [2:0] a_idx, b_idx;
  wire       a_zero, neg, first;

  bitserial_seq #(.ACC_W(18)) seq (
      .clk(clk), .rst_n(rst_n), .en(en), .clr(clr),
      .a_idx(a_idx), .a_zero(a_zero), .b_idx(b_idx), .neg(neg), .first(first), .last(last)
  );

  mac_bitserial #(.ACC_W(18)) mac (
      .clk(clk), .rst_n(rst_n), .en(en), .clr(clr), .a(a), .b(b),
      .a_idx(a_idx), .a_zero(a_zero), .b_idx(b_idx), .neg(neg), .first(first),
      .acc(acc)
  );
endmodule
