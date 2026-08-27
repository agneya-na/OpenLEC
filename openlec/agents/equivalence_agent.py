"""Runs the LEC gate (Conformal: COMPARE)."""
from __future__ import annotations

from openlec.agents import BaseAgent
from openlec.engine.lec_engine import LECEngine
from openlec.engine.yosys_runner import YosysRunner
from openlec.models.lec_result import LECVerdict
from openlec.models.schemas import VerificationContext


class EquivalenceAgent(BaseAgent):
    name = "equivalence"

    def __init__(self, runner: YosysRunner | None = None) -> None:
        self.lec = LECEngine(runner)

    def execute(self, ctx: VerificationContext) -> VerificationContext:
        if ctx.halted:
            return ctx
        result = self.lec.run_equivalence_check(
            str(ctx.golden_netlist), str(ctx.revised_netlist), ctx.top_module
        )
        ctx.lec_result = result
        if result.verdict is LECVerdict.NONEQUIVALENT:
            ctx.halt(f"LEC NONEQUIVALENT: {result.message}")
        elif result.verdict is LECVerdict.ABORT:
            self.log(ctx, f"LEC inconclusive (abort): {result.message}")
        else:
            self.log(ctx, "LEC gate: EQUIVALENT")
        return ctx
