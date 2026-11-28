`include "accum_cfg.svh"

module accum_top (
    input  logic                  clk,
    input  logic                  rst,
    input  logic                  valid_in,
    input  logic [7:0]            a,
    input  logic [7:0]            b,
    output logic [`ACC_WIDTH-1:0] acc,
    output logic                  valid_out
);
    accum_core u_core (
        .clk(clk), .rst(rst), .valid_in(valid_in), .a(a), .b(b), .acc(acc)
    );

    always_ff @(posedge clk or posedge rst) begin
        if (rst) valid_out <= 1'b0;
        else     valid_out <= valid_in;
    end
endmodule
