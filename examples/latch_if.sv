module latch_if (
    input  logic       en_i,
    input  logic [3:0] data_i,
    output logic [3:0] data_o
);
  // BUG: no else -> data_o holds previous value -> inferred latch
  always @* begin
    if (en_i) begin
      data_o = data_i;
    end
  end
endmodule