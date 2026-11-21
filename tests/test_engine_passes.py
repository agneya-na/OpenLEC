"""Tests for the Yosys runner, netlist stats, estimators and optimizer.

Unit tests use fake runners (or Python standing in for the Yosys binary);
integration tests run real Yosys and skip when it is absent.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from openlec.agents.optimization_agent import OptimizationAgent
from openlec.engine.netlist_stats import NetlistStats, parse_stat_json
from openlec.engine.optimizer import Optimizer
from openlec.engine.power_estimator import PowerEstimator
from openlec.engine.timing_estimator import TimingEstimator
from openlec.engine.yosys_runner import YosysError, YosysRunner, quote_path
from openlec.models.optimization_step import StepVerdict
from openlec.models.schemas import VerificationContext

requires_yosys = pytest.mark.skipif(
    shutil.which("yosys") is None,
    reason="Yosys not installed; skipping Yosys integration tests.",
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "designs"

# `stat -json` as printed by Yosys 0.71 (banner and other log lines around it).
STAT_LOG = """\
 Yosys 0.71 (git sha1 b4c586fd3, Release)
5. Printing statistics.
{
   "creator": "Yosys 0.71",
   "invocation": "stat -json ",
   "modules": {
      "\\\\top": {
         "num_cells":         5,
         "num_cells_by_type": {"$add": 1, "$adff": 2, "$scopeinfo": 2}
      }
   },
   "design": {
      "num_cells":         5,
      "num_cells_by_type": {"$add": 1, "$adff": 2, "$scopeinfo": 2}
   }
}

End of script.
"""

# Older Yosys releases have no "design" block, only per-module blocks.
STAT_LOG_MODULES_ONLY = """\
{
   "creator": "Yosys 0.23",
   "modules": {
      "\\\\top": {"num_cells": 4, "num_cells_by_type": {"$_AND_": 2, "$_DFF_P_": 2}}
   }
}
"""


class _StatRunner:
    def __init__(self, log=STAT_LOG):
        self.log = log
        self.calls = 0

    def run_script(self, script):
        self.calls += 1
        return self.log


# ---------------------------------------------------------------- runner
class TestYosysRunner:
    """A Python interpreter stands in for Yosys: `python -s script` runs the script."""

    def test_error_lines_from_stdout_are_reported(self):
        runner = YosysRunner(sys.executable)

        with pytest.raises(YosysError) as exc:
            runner.run_script("print('ERROR: Re-definition of module leaf')\nraise SystemExit(1)\n")

        assert "ERROR: Re-definition of module leaf" in str(exc.value)
        assert "Re-definition" in exc.value.log

    def test_timeout_raises(self):
        runner = YosysRunner(sys.executable, timeout_seconds=0.5)

        with pytest.raises(YosysError, match="timed out"):
            runner.run_script("import time\ntime.sleep(10)\n")

    def test_missing_binary_raises(self):
        with pytest.raises(YosysError, match="not found"):
            YosysRunner("definitely-not-yosys-xyz").run_script("")

    def test_success_returns_stdout(self):
        assert YosysRunner(sys.executable).run_script("print('ok')\n").strip() == "ok"


def test_quote_path():
    assert quote_path(Path("my dir") / "top.v") == '"my dir/top.v"'
    with pytest.raises(ValueError):
        quote_path('bad"name.v')


# ---------------------------------------------------------------- stats
class TestNetlistStats:
    def test_parses_design_block_and_skips_bookkeeping_cells(self):
        assert parse_stat_json(STAT_LOG, "top") == NetlistStats(cells=3, registers=2)

    def test_falls_back_to_top_module_block(self):
        assert parse_stat_json(STAT_LOG_MODULES_ONLY, "top") == NetlistStats(cells=4, registers=2)

    def test_unparseable_log_gives_zero(self):
        assert parse_stat_json("Number of cells: 12\n", "top") == NetlistStats()


class TestEstimators:
    def test_timing_estimate_is_nonzero_and_cached(self, tmp_path):
        rtl = tmp_path / "top.v"
        rtl.write_text("module top; endmodule\n")
        runner = _StatRunner()
        timing = TimingEstimator(runner)

        delay = timing.estimate(rtl, "top")
        cells = timing.cell_count(rtl, "top")

        assert delay > 0
        assert cells == 3
        assert runner.calls == 1  # estimate + cell_count share one Yosys run

    def test_power_estimate_is_nonzero(self, tmp_path):
        rtl = tmp_path / "top.v"
        rtl.write_text("module top; endmodule\n")

        assert PowerEstimator(_StatRunner()).estimate(rtl, "top") > 0

    def test_yosys_failure_gives_zero(self, tmp_path):
        class _Failing:
            def run_script(self, script):
                raise YosysError("boom")

        assert TimingEstimator(_Failing()).estimate(tmp_path / "x.v", "top") == 0.0


# ---------------------------------------------------------------- optimizer
def test_optimizer_runs_proc_before_pass_and_quotes_paths(tmp_path):
    src = tmp_path / "in dir" / "top.v"
    src.parent.mkdir()
    src.write_text("module top; endmodule\n")
    out_dir = tmp_path / "out dir"

    class _Runner:
        script = ""

        def run_script(self, script):
            _Runner.script = script
            (out_dir / "optimized_iter1.v").write_text("module top; endmodule\n")
            return ""

    out = Optimizer(_Runner()).apply(src, "share", "top", 1, out_dir=out_dir)
    lines = _Runner.script.splitlines()

    assert out == out_dir / "optimized_iter1.v"
    assert lines.index("proc") < lines.index("share")
    assert f"read_verilog {quote_path(src)}" in lines
    assert f"write_verilog -noattr {quote_path(out)}" in lines


# ---------------------------------------------------------------- integration
@requires_yosys
def test_stats_on_example_design():
    stats = TimingEstimator().stats(EXAMPLES / "mac_unit.v", "mac_unit")

    assert stats.cells > 0
    assert stats.registers > 0


@requires_yosys
def test_optimizer_passes_survive_lec_gate(tmp_path):
    rtl = EXAMPLES / "counter.v"
    ctx = VerificationContext(rtl_file=rtl, top_module="counter", iterations=5,
                              delay_budget_ns=10.0, power_budget_uw=1000.0)
    ctx.golden_netlist = rtl
    ctx.revised_netlist = rtl

    ctx = OptimizationAgent().execute(ctx)

    accepted = [s for s in ctx.steps if s.verdict is StepVerdict.ACCEPT]
    assert accepted, [s.reject_reason for s in ctx.steps]
    assert all(s.metrics and s.metrics.area_cells > 0 for s in accepted)
