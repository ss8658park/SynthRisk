module legacy_always (
    input  logic clk_i,
    input  logic rst_n_i,
    input  logic d_i,
    output logic q_o
);
  // BUG: plain always instead of always_ff -> intent not enforced
  always @(posedge clk_i or negedge rst_n_i) begin
    if (!rst_n_i) q_o = 1'b0;   // BUG: blocking assignment in sequential logic
    else          q_o = d_i;
  end
endmodule