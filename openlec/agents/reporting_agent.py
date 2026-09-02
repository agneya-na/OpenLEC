"""Builds and renders the final verification report."""
from __future__ import annotations

from openlec.agents import BaseAgent
from openlec.models.lec_result import LECVerdict
from openlec.models.schemas import VerificationContext, VerificationReport


class ReportingAgent(BaseAgent):
    name = "reporting"

    def execute(self, ctx: VerificationContext) -> VerificationContext:
        lec_ok = ctx.lec_result is not None and ctx.lec_result.verdict is LECVerdict.EQUIVALENT
        upf_ok = all(r.passed for r in ctx.upf_checks.values()) if ctx.upf_checks else True
        passed = (not ctx.halted) and lec_ok and upf_ok
        summary = ctx.halt_reason if ctx.halted else (
            "All gates passed (LEC + UPF + budgets)." if passed
            else "One or more gates failed or were inconclusive."
        )
        ctx.report = VerificationReport(
            passed=passed, summary=summary, lec_result=ctx.lec_result,
            upf_checks=ctx.upf_checks, metrics=ctx.metrics, steps=ctx.steps,
        )
        return ctx

    @staticmethod
    def render(report: VerificationReport) -> str:
        return report.to_text()