// Shared configuration for the SystemVerilog accumulator example.
`ifndef ACCUM_CFG_SVH
`define ACCUM_CFG_SVH

// Accumulator width; override with -D ACC_WIDTH=<n> (must be >= 9).
`ifndef ACC_WIDTH
`define ACC_WIDTH 16
`endif

`endif
