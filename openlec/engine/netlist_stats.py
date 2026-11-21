"""Cell and register counts from Yosys ``stat -json`` (shared by the estimators).

The JSON form is used instead of scraping the text table, whose layout
changed across Yosys releases (``Number of cells: N`` vs ``N cells``).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openlec.engine.yosys_runner import YosysRunner, quote_path

logger = logging.getLogger(__name__)

# Bookkeeping cells that carry no logic (added by `flatten` in newer Yosys).
_IGNORED_CELL_TYPES = frozenset({"$scopeinfo"})
# $dff, $adff, $sdff..., $_DFF_P_, $dlatch, $_DLATCH_P_, $ff, $_FF_, Liberty DFF* cells.
_REGISTER_RE = re.compile(r"dff|latch|^\$_?ff_?$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class NetlistStats:
    cells: int = 0
    registers: int = 0


def parse_stat_json(log: str, top_module: str) -> NetlistStats:
    """Extract the design (or top module) cell counts from a `stat -json` log."""
    anchor = log.find('"creator"')
    start = log.rfind("{", 0, anchor) if anchor >= 0 else -1
    if start < 0:
        return NetlistStats()
    try:
        data, _ = json.JSONDecoder().raw_decode(log[start:])
    except ValueError:
        return NetlistStats()

    modules: dict[str, Any] = data.get("modules") or {}
    block: dict[str, Any] = (
        data.get("design")
        or modules.get(f"\\{top_module}")
        or modules.get(top_module)
        or {}
    )
    by_type: dict[str, int] = block.get("num_cells_by_type") or {}
    if by_type:
        cells = sum(n for t, n in by_type.items() if t not in _IGNORED_CELL_TYPES)
    else:
        cells = int(block.get("num_cells", 0))
    registers = sum(n for t, n in by_type.items() if _REGISTER_RE.search(t))
    return NetlistStats(cells=cells, registers=registers)


def collect_stats(runner: YosysRunner, netlist: str | Path, top_module: str) -> NetlistStats:
    """Elaborate and flatten the netlist in Yosys, then count its cells."""
    script = (
        f"read_verilog {quote_path(netlist)}\n"
        f"hierarchy -check -top {top_module}\n"
        "proc\n"
        "flatten\n"
        "opt_clean\n"
        "stat -json\n"
    )
    try:
        log = runner.run_script(script)
    except RuntimeError as exc:
        logger.warning("Could not collect netlist stats for %s: %s", netlist, exc)
        return NetlistStats()
    return parse_stat_json(log, top_module)
