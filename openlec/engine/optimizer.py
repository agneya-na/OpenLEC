"""Synthesis pass proposal/application engine."""
from __future__ import annotations

from pathlib import Path
from tempfile import mkdtemp

from openlec.engine.design_source import NetlistLike, as_source
from openlec.engine.yosys_runner import YosysRunner, quote_path

DEFAULT_PASSES = (
    "opt",
    "opt_clean",
    "fsm",
    "share",
    "abc",
)


class Optimizer:
    def __init__(self, runner: YosysRunner | None = None) -> None:
        self.runner = runner or YosysRunner()
        self.passes = DEFAULT_PASSES

    def propose(self, iteration: int) -> str | None:
        index = iteration - 1
        if index < 0 or index >= len(self.passes):
            return None
        return self.passes[index]

    def apply(
        self,
        netlist: NetlistLike,
        pass_cmd: str,
        top_module: str,
        iteration: int,
        out_dir: str | Path | None = None,
    ) -> Path:
        source = as_source(netlist)
        missing = source.missing()
        if missing:
            kind, path = missing[0]
            raise RuntimeError(f"Netlist {kind} not found: {path}")
        try:
            read = source.read_script()
        except ValueError as exc:  # bad design source option
            raise RuntimeError(str(exc)) from None

        output_dir = Path(out_dir) if out_dir else Path(mkdtemp(prefix="openlec_opt_"))
        output_dir.mkdir(parents=True, exist_ok=True)
        out_netlist = output_dir / f"optimized_iter{iteration}.v"

        # `proc` must run before any pass: without it Yosys writes the raw
        # processes back out and `always @(posedge clk or posedge rst)` is split
        # into two separate always blocks, which changes the design.
        script = (
            read
            + f"hierarchy -check -top {top_module}\n"
            "proc\n"
            f"{pass_cmd}\n"
            "opt_clean -purge\n"
            f"write_verilog -noattr {quote_path(out_netlist)}\n"
        )
        self.runner.run_script(script)
        if not out_netlist.exists():
            raise RuntimeError(
                f"Optimizer pass '{pass_cmd}' did not produce output netlist {out_netlist}"
            )
        return out_netlist


# Backward-compatible alias for older imports.
OptimizationEngine = Optimizer
