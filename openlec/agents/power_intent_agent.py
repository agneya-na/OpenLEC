"""UPF conformity gate (Conformal: CHECK LOWPOWER CELLS / COMPARE POWER CONSISTENCY)."""
from __future__ import annotations

from openlec.agents import BaseAgent
from openlec.engine.upf_checker import UPFChecker
from openlec.models.schemas import VerificationContext


class PowerIntentAgent(BaseAgent):
    name = "power_intent"

    def execute(self, ctx: VerificationContext) -> VerificationContext:
        if ctx.halted or ctx.upf_intent is None:
            return ctx
        checker = UPFChecker(
            ctx.upf_intent,
            netlist_ast={"isolated_domains": sorted(ctx.upf_intent.isolated_domains())},
        )
        ctx.upf_checks = checker.run_all_checks()
        for family, result in ctx.upf_checks.items():
            if result.passed:
                self.log(ctx, f"UPF {family}: PASS")
            elif family == "isolation":
                ctx.halt(f"UPF isolation violations: {result.violations}")
            else:
                self.log(ctx, f"UPF {family} warnings: {result.violations}")
        return ctx
