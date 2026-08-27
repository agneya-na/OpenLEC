"""Builds and renders the final verification report."""
from __future__ import annotations

from openlec.agents import BaseAgent
from openlec.models.lec_result import LECVerdict
from openlec.models.optimization_step import StepVerdict
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
        bar = "=" * 62
        lines = [bar, "OpenLEC Verification Report", bar,
                 f"Status : {'PASS' if report.passed else 'FAIL'}",
                 f"Summary: {report.summary}"]
        if report.lec_result:
            lines.append(f"LEC    : {report.lec_result.verdict.value} - {report.lec_result.message}")
        if report.upf_checks:
            for family, res in report.upf_checks.items():
                lines.append(f"UPF {family:<9}: {'PASS' if res.passed else 'FAIL'}"
                             + (f" - {res.violations}" if res.violations else ""))
        if report.metrics:
            lines.append(f"Metrics: delay={report.metrics.delay_ns}ns "
                         f"power={report.metrics.power_uw}uW cells={report.metrics.area_cells}")
        if report.steps:
            lines.append("-" * 62)
            for step in report.steps:
                tag = "ACCEPT" if step.verdict is StepVerdict.ACCEPT else "REJECT"
                extra = step.reject_reason if step.verdict is StepVerdict.REJECT else step.pass_name
                lines.append(f"[{tag}] iter {step.iteration}: {extra}")
            accepted = sum(1 for s in report.steps if s.verdict is StepVerdict.ACCEPT)
            lines.append(f"Accepted optimization steps: {accepted}")
        lines += [bar, f"Generated at: {report.generated_at}", bar]
        return "\n".join(lines)