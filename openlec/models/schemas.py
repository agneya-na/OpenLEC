"""Flow-level schemas: verification context and final report."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from openlec.models.lec_result import LECResult
from openlec.models.metrics import DesignMetrics
from openlec.models.optimization_step import OptimizationStep, StepVerdict
from openlec.models.upf_models import UPFCheckResult, UPFIntent


@dataclass
class VerificationContext:
    """Mutable state shared by all agents during one verification run."""

    rtl_file: Path
    top_module: str
    upf_file: Optional[Path] = None
    iterations: int = 3
    delay_budget_ns: float = 10.0
    power_budget_uw: float = 1000.0
    verbose: bool = False

    # Produced along the flow
    upf_intent: Optional[UPFIntent] = None
    golden_netlist: Optional[Path] = None
    revised_netlist: Optional[Path] = None
    lec_result: Optional[LECResult] = None
    upf_checks: Dict[str, UPFCheckResult] = field(default_factory=dict)
    baseline_metrics: Optional[DesignMetrics] = None
    metrics: Optional[DesignMetrics] = None
    steps: List[OptimizationStep] = field(default_factory=list)
    halted: bool = False
    halt_reason: str = ""
    report: Optional["VerificationReport"] = None

    def halt(self, reason: str) -> None:
        self.halted = True
        self.halt_reason = reason


@dataclass
class VerificationReport:
    """Final report emitted by the ReportingAgent."""

    passed: bool
    summary: str
    lec_result: Optional[LECResult] = None
    upf_checks: Dict[str, UPFCheckResult] = field(default_factory=dict)
    metrics: Optional[DesignMetrics] = None
    steps: List[OptimizationStep] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    @property
    def accepted_steps(self) -> List[OptimizationStep]:
        return [s for s in self.steps if s.verdict is StepVerdict.ACCEPT]
