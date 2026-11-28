"""Heuristic static timing estimator (placeholder until OpenSTA integration).

Derives a conservative delay from the Yosys cell count:
estimated logic levels ~ log2(cells), one gate delay per level.
"""
from __future__ import annotations

import math

from openlec.engine.design_source import NetlistLike, as_source
from openlec.engine.netlist_stats import NetlistStats, collect_stats
from openlec.engine.yosys_runner import YosysRunner

GATE_DELAY_NS = 0.05


class TimingEstimator:
    def __init__(self, runner: YosysRunner | None = None) -> None:
        self.runner = runner or YosysRunner()
        self._cache: dict[tuple[object, ...], NetlistStats] = {}

    def stats(self, netlist: NetlistLike, top_module: str) -> NetlistStats:
        """Cell/register counts, cached per (files + mtimes, options, top)."""
        source = as_source(netlist)
        key = (source.cache_key(), top_module)
        if key not in self._cache:
            self._cache[key] = collect_stats(self.runner, source, top_module)
        return self._cache[key]

    def cell_count(self, netlist: NetlistLike, top_module: str) -> int:
        return self.stats(netlist, top_module).cells

    def estimate(self, netlist: NetlistLike, top_module: str) -> float:
        cells = self.stats(netlist, top_module).cells
        if cells <= 0:
            return 0.0
        levels = max(1, int(math.log2(max(2, cells))))
        return round(levels * GATE_DELAY_NS, 3)
