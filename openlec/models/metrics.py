"""Design metrics (single source of truth)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DesignMetrics:
    delay_ns: float = 0.0
    power_uw: float = 0.0
    area_cells: int = 0

    def within_budget(self, delay_budget_ns: float, power_budget_uw: float) -> bool:
        return self.delay_ns <= delay_budget_ns and self.power_uw <= power_budget_uw


Metrics = DesignMetrics  # backward-compatible alias
