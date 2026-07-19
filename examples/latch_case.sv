module latch_case (
    input  logic [2:0] cmd_i,
    output logic       rd_o,
    output logic       wr_o
);
  // BUG: no default -> outputs hold value for uncovered cmd_i -> inferred latch
  always @* begin
    case (cmd_i)
      3'b001: begin rd_o = 1'b1; wr_o = 1'b0; end
      3'b010: begin rd_o = 1'b0; wr_o = 1'b1; end
    endcase
  end
endmodule