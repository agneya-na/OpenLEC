"""Proposes synthesis passes and enforces LEC + metrics gates per step."""
from __future__ import annotations

from openlec.agents import BaseAgent
from openlec.engine.lec_engine import LECEngine
from openlec.engine.optimizer import Optimizer
from openlec.engine.power_estimator import PowerEstimator
from openlec.engine.timing_estimator import TimingEstimator
from openlec.engine.yosys_runner import YosysRunner
from openlec.models.lec_result import LECVerdict
from openlec.models.metrics import DesignMetrics
from openlec.models.optimization_step import OptimizationStep, StepVerdict
from openlec.models.schemas import VerificationContext


class OptimizationAgent(BaseAgent):
    name = "optimization"

    def __init__(self, runner: YosysRunner | None = None) -> None:
        self.runner = runner or YosysRunner()
        self.optimizer = Optimizer(self.runner)
        self.lec = LECEngine(self.runner)
        self.timing = TimingEstimator(self.runner)
        self.power = PowerEstimator(self.runner)

    def execute(self, ctx: VerificationContext) -> VerificationContext:
        if ctx.halted:
            return ctx
        for iteration in range(1, ctx.iterations + 1):
            pass_cmd = self.optimizer.propose(iteration)
            if pass_cmd is None:
                break
            if ctx.revised_netlist is None:
                ctx.halt("Optimization requires a revised netlist.")
                break
            try:
                new_netlist = self.optimizer.apply(
                    ctx.revised_netlist, pass_cmd, ctx.top_module, iteration
                )
            except RuntimeError as exc:
                ctx.steps.append(
                    OptimizationStep(
                        iteration=iteration,
                        pass_name=pass_cmd,
                        verdict=StepVerdict.REJECT,
                        reject_reason=str(exc),
                        revised_netlist=str(ctx.revised_netlist),
                    )
                )
                continue

            lec = self.lec.run_equivalence_check(
                str(ctx.golden_netlist), str(new_netlist), ctx.top_module
            )
            if lec.verdict is not LECVerdict.EQUIVALENT:
                ctx.steps.append(
                    OptimizationStep(
                        iteration=iteration,
                        pass_name=pass_cmd,
                        verdict=StepVerdict.REJECT,
                        reject_reason=f"LEC gate failed ({lec.verdict.value})",
                        revised_netlist=str(ctx.revised_netlist),
                    )
                )
                continue

            metrics = DesignMetrics(
                delay_ns=self.timing.estimate(new_netlist, ctx.top_module),
                power_uw=self.power.estimate(new_netlist, ctx.top_module),
                area_cells=ctx.metrics.area_cells if ctx.metrics else 0,
            )
            if not metrics.within_budget(ctx.delay_budget_ns, ctx.power_budget_uw):
                ctx.steps.append(
                    OptimizationStep(
                        iteration=iteration,
                        pass_name=pass_cmd,
                        verdict=StepVerdict.REJECT,
                        reject_reason=(
                            "Metrics out of budget "
                            f"(delay={metrics.delay_ns}ns, power={metrics.power_uw}uW)"
                        ),
                        revised_netlist=str(ctx.revised_netlist),
                        metrics=metrics,
                    )
                )
                continue

            ctx.metrics = metrics
            ctx.steps.append(
                OptimizationStep(
                    iteration=iteration,
                    pass_name=pass_cmd,
                    verdict=StepVerdict.ACCEPT,
                    revised_netlist=str(new_netlist),
                    metrics=metrics,
                )
            )
            ctx.revised_netlist = str(new_netlist)
            self.log(ctx, f"iter {iteration}: ACCEPT '{pass_cmd}'")
        return ctx