// SystemVerilog accumulator example, split across files with a shared include.
// Paths are relative to this list, so read it with -F:
//   openlec -F examples/designs/sv/accum_top.f --top accum_top
+incdir+include
rtl/accum_core.sv
rtl/accum_top.sv
