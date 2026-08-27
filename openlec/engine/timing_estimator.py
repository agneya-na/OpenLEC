"""Heuristic static timing estimator (placeholder until OpenSTA integration).

Derives a conservative delay from Yosys ``stat`` output:
estimated logic levels ~ log2(cells), one gate delay per level.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from openlec.engine.yosys_runner import YosysRunner

GATE_DELAY_NS = 0.05


class TimingEstimator:
    def __init__(self, runner: YosysRunner | None = None) -> None:
        self.runner = runner or YosysRunner()

    def estimate(self, netlist: str | Path, top_module: str) -> float:
        cells, _regs = self._cell_stats(netlist, top_module)
        if cells <= 0:
            return 0.0
        levels = max(1, int(math.log2(max(2, cells))))
        return round(levels * GATE_DELAY_NS, 3)

    def _cell_stats(self, netlist: str | Path, top_module: str) -> tuple[int, int]:
        try:
            out = self.runner.run_script(
                f"read_verilog {netlist}\nhierarchy -top {top_module}\nstat\n"
            )
        except RuntimeError:
            return 0, 0
        cells_m = re.search(r"Number of cells:\s+(\d+)", out)
        cells = int(cells_m.group(1)) if cells_m else 0
        regs = sum(int(n) for n in re.findall(r"\$_D(?:FF|LAT)\w*\s+(\d+)", out))
        return cells, regs
