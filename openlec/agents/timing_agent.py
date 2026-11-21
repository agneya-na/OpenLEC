"""Timing gate (placeholder estimator until OpenSTA integration)."""
from __future__ import annotations

from openlec.agents import BaseAgent
from openlec.engine.timing_estimator import TimingEstimator
from openlec.engine.yosys_runner import YosysRunner
from openlec.models.metrics import DesignMetrics
from openlec.models.schemas import VerificationContext


class TimingAgent(BaseAgent):
    name = "timing"

    def __init__(self, runner: YosysRunner | None = None) -> None:
        self.estimator = TimingEstimator(runner)

    def execute(self, ctx: VerificationContext) -> VerificationContext:
        if ctx.halted:
            return ctx
        netlist = ctx.revised_netlist or ""
        delay = self.estimator.estimate(netlist, ctx.top_module)
        cells = self.estimator.cell_count(netlist, ctx.top_module)
        prev = ctx.metrics
        ctx.metrics = DesignMetrics(
            delay_ns=delay,
            power_uw=prev.power_uw if prev else 0.0,
            area_cells=cells,
        )
        if delay > ctx.delay_budget_ns:
            self.log(ctx, f"Delay {delay}ns exceeds budget {ctx.delay_budget_ns}ns (warning)")
        else:
            self.log(ctx, f"Timing gate: {delay}ns within budget {ctx.delay_budget_ns}ns")
        return ctx