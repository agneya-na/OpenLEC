# models/optimization_step.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from .metrics import DesignMetrics

class Verdict(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"

@dataclass(slots=True)
class OptimizationStep:
    iteration: int
    pass_name: str
    verdict: Verdict
    reject_reason: str = ""
    revised_netlist: str = ""
    metrics: Optional[DesignMetrics] = None
