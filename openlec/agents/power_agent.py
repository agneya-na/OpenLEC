"""Power gate (placeholder estimator until Liberty/VCD integration)."""
from __future__ import annotations

from openlec.agents import BaseAgent
from openlec.engine.power_estimator import PowerEstimator
from openlec.engine.yosys_runner import YosysRunner
from openlec.models.metrics import DesignMetrics
from openlec.models.schemas import VerificationContext


class PowerAgent(BaseAgent):
    name = "power"

    def __init__(self, runner: YosysRunner | None = None) -> None:
        self.estimator = PowerEstimator(runner)

    def execute(self, ctx: VerificationContext) -> VerificationContext:
        if ctx.halted:
            return ctx
        power = self.estimator.estimate(ctx.revised_netlist or "", ctx.top_module)
        prev = ctx.metrics or DesignMetrics()
        ctx.metrics = DesignMetrics(delay_ns=prev.delay_ns, power_uw=power, area_cells=prev.area_cells)
        if ctx.baseline_metrics is None:
            ctx.baseline_metrics = ctx.metrics
        if power > ctx.power_budget_uw:
            self.log(ctx, f"Power {power}uW exceeds budget {ctx.power_budget_uw}uW (warning)")
        else:
            self.log(ctx, f"Power gate: {power}uW within budget {ctx.power_budget_uw}uW")
        return ctx