# models/optimization_step.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .metrics import DesignMetrics


class Verdict(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"


# Canonical enum name used by agents/reporting/tests.
StepVerdict = Verdict

@dataclass(slots=True)
class OptimizationStep:
    iteration: int
    pass_name: str
    verdict: Verdict
    reject_reason: str = ""
    revised_netlist: str = ""
    metrics: DesignMetrics | None = None
