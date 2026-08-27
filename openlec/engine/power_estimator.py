"""Heuristic power estimator (placeholder until Liberty/VCD integration).

power = dynamic(activity * cells * per-cell dynamic) + leakage(cells + registers).
"""
from __future__ import annotations

from pathlib import Path

from openlec.engine.timing_estimator import TimingEstimator
from openlec.engine.yosys_runner import YosysRunner

DYNAMIC_UW_PER_CELL = 0.5
ACTIVITY_FACTOR = 0.2
LEAK_UW_PER_CELL = 0.002
LEAK_UW_PER_REG = 0.01


class PowerEstimator:
    def __init__(self, runner: YosysRunner | None = None) -> None:
        self.runner = runner or YosysRunner()
        self._stats = TimingEstimator(self.runner)

    def estimate(self, netlist: str | Path, top_module: str) -> float:
        cells, regs = self._stats._cell_stats(netlist, top_module)
        if cells <= 0:
            return 0.0
        dynamic = cells * DYNAMIC_UW_PER_CELL * ACTIVITY_FACTOR
        leakage = cells * LEAK_UW_PER_CELL + regs * LEAK_UW_PER_REG
        return round(dynamic + leakage, 3)
