"""Flow-level schemas: verification context and final report."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from openlec.models.lec_result import LECResult
from openlec.models.metrics import DesignMetrics
from openlec.models.optimization_step import OptimizationStep, StepVerdict
from openlec.models.upf_models import UPFCheckResult, UPFIntent


@dataclass
class VerificationContext:
    """Mutable state shared by all agents during one verification run."""

    rtl_file: Path
    top_module: str
    upf_file: Path | None = None
    iterations: int = 3
    delay_budget_ns: float = 10.0
    power_budget_uw: float = 1000.0
    verbose: bool = False

    # Produced along the flow
    upf_intent: UPFIntent | None = None
    golden_netlist: Path | str | None = None
    revised_netlist: Path | str | None = None
    lec_result: LECResult | None = None
    upf_checks: dict[str, UPFCheckResult] = field(default_factory=dict)
    baseline_metrics: DesignMetrics | None = None
    metrics: DesignMetrics | None = None
    steps: list[OptimizationStep] = field(default_factory=list)
    halted: bool = False
    halt_reason: str = ""
    report: VerificationReport | None = None

    def halt(self, reason: str) -> None:
        self.halted = True
        self.halt_reason = reason


@dataclass
class VerificationReport:
    """Final report emitted by the ReportingAgent."""

    passed: bool
    summary: str
    lec_result: LECResult | None = None
    upf_checks: dict[str, UPFCheckResult] = field(default_factory=dict)
    metrics: DesignMetrics | None = None
    steps: list[OptimizationStep] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    @property
    def accepted_steps(self) -> list[OptimizationStep]:
        return [s for s in self.steps if s.verdict is StepVerdict.ACCEPT]

    def to_text(self) -> str:
        bar = "=" * 62
        lines = [
            bar,
            "OpenLEC Verification Report",
            bar,
            f"Status : {'PASS' if self.passed else 'FAIL'}",
            f"Summary: {self.summary}",
        ]
        if self.lec_result:
            lines.append(f"LEC    : {self.lec_result.verdict.value} - {self.lec_result.message}")
        if self.upf_checks:
            for family, res in self.upf_checks.items():
                lines.append(
                    f"UPF {family:<9}: {'PASS' if res.passed else 'FAIL'}"
                    + (f" - {res.violations}" if res.violations else "")
                )
        if self.metrics:
            lines.append(
                f"Metrics: delay={self.metrics.delay_ns}ns "
                f"power={self.metrics.power_uw}uW cells={self.metrics.area_cells}"
            )
        if self.steps:
            lines.append("-" * 62)
            for step in self.steps:
                tag = "ACCEPT" if step.verdict is StepVerdict.ACCEPT else "REJECT"
                extra = step.reject_reason if step.verdict is StepVerdict.REJECT else step.pass_name
                lines.append(f"[{tag}] iter {step.iteration}: {extra}")
            lines.append(f"Accepted optimization steps: {len(self.accepted_steps)}")
        lines += [bar, f"Generated at: {self.generated_at}", bar]
        return "\n".join(lines)
