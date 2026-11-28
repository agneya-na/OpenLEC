"""Builds and renders the final verification report."""
from __future__ import annotations

from openlec.agents import BaseAgent
from openlec.models.lec_result import LECVerdict
from openlec.models.schemas import VerificationContext, VerificationReport


class ReportingAgent(BaseAgent):
    name = "reporting"

    def execute(self, ctx: VerificationContext) -> VerificationContext:
        failed = self._failed_gates(ctx)
        passed = not ctx.halted and not failed
        if ctx.halted:
            summary = ctx.halt_reason
        elif passed:
            summary = "All gates passed (LEC + UPF + budgets)."
        else:
            summary = "Failed gates: " + "; ".join(failed)
        ctx.report = VerificationReport(
            passed=passed, summary=summary, lec_result=ctx.lec_result,
            upf_checks=ctx.upf_checks, metrics=ctx.metrics, steps=ctx.steps,
            golden_file=str(ctx.golden_source or ctx.rtl_file),
            revised_file=str(
                ctx.revised_source or ctx.revised_file or ctx.golden_source or ctx.rtl_file
            ),
        )
        return ctx

    @staticmethod
    def _failed_gates(ctx: VerificationContext) -> list[str]:
        failed: list[str] = []
        if ctx.lec_result is None:
            failed.append("LEC (not run)")
        elif ctx.lec_result.verdict is not LECVerdict.EQUIVALENT:
            failed.append(f"LEC ({ctx.lec_result.verdict.value})")
        failed += [f"UPF {family}" for family, r in ctx.upf_checks.items() if not r.passed]
        m = ctx.metrics
        if m is not None and m.delay_ns > ctx.delay_budget_ns:
            failed.append(f"timing budget ({m.delay_ns}ns > {ctx.delay_budget_ns}ns)")
        if m is not None and m.power_uw > ctx.power_budget_uw:
            failed.append(f"power budget ({m.power_uw}uW > {ctx.power_budget_uw}uW)")
        return failed

    @staticmethod
    def render(report: VerificationReport) -> str:
        return report.to_text()
