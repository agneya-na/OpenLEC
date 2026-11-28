`include "accum_cfg.svh"

module accum_core (
    input  logic                  clk,
    input  logic                  rst,
    input  logic                  valid_in,
    input  logic [7:0]            a,
    input  logic [7:0]            b,
    output logic [`ACC_WIDTH-1:0] acc
);
    logic [8:0] sum;

    always_comb sum = a + b;

    always_ff @(posedge clk or posedge rst) begin
        if (rst)           acc <= {`ACC_WIDTH{1'b0}};
        else if (valid_in) acc <= acc + sum;
    end
endmodule
