// Clean reference: complete assignments, explicit intent, no latch risk
module clean (
    input  logic       clk_i,
    input  logic       rst_n_i,
    input  logic       en_i,
    input  logic [3:0] data_i,
    output logic [3:0] data_o,
    output logic       valid_o
);
 
  // Combinational: always_comb + default assignment covers every path
  logic [3:0] next_data;
  always_comb begin
    next_data = 4'h0;
    if (en_i) begin
      next_data = data_i;
    end
  end
 
  // Sequential: always_ff + non-blocking assignments
  always_ff @(posedge clk_i or negedge rst_n_i) begin
    if (!rst_n_i) begin
      data_o  <= 4'h0;
      valid_o <= 1'b0;
    end else begin
      data_o  <= next_data;
      valid_o <= en_i;
    end
  end
 
endmodule