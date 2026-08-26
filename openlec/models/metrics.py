# models/metrics.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class DesignMetrics:
    delay_ns: float = 0.0
    power_uw: float = 0.0
    area_cells: int = 0
