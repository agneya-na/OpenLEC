module mac_unit (
    input             clk,
    input             rst,
    input             valid_in,
    input      [7:0]  a,
    input      [7:0]  b,
    output reg [15:0] acc,
    output reg        valid_out
);
    wire [15:0] product = a * b;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            acc       <= 16'b0;
            valid_out <= 1'b0;
        end else begin
            acc       <= valid_in ? (acc + product) : acc;
            valid_out <= valid_in;
        end
    end
endmodule