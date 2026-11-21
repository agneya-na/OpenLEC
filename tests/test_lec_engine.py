"""LEC engine tests.

Unit tests replay Yosys log excerpts through a scripted runner (no Yosys
needed). Integration tests run the real flow and skip when Yosys is absent.
"""
from __future__ import annotations

import shutil

import pytest

from openlec.engine.lec_engine import LECEngine
from openlec.engine.yosys_runner import YosysError
from openlec.models.lec_result import LECVerdict

requires_yosys = pytest.mark.skipif(
    shutil.which("yosys") is None,
    reason="Yosys not installed; skipping LEC integration tests.",
)

# ---------------------------------------------------------------- recorded logs
# Excerpts of real Yosys 0.71 output.
PROVEN_LOG = """\
Found 1 unproven $equiv cells (1 groups) in equiv:
Proved 1 previously unproven $equiv cells.
13. Executing EQUIV_STATUS pass.
Found 1 $equiv cells in equiv:
  Of those cells 1 are proven and 0 are unproven.
  Equivalence successfully proven!
"""

# Words like "failed" and "SAT" appear on the way to a successful proof; they
# must not affect the verdict (the old keyword scraper turned this into ABORT).
PROVEN_AFTER_RETRIES_LOG = """\
Executing SAT pass (solving SAT problems in the circuit).
  Proof for induction step failed. Extending to next time step.
  Proof for induction step holds. Entire workset of 4 cells proven!
Presumably equivalent wires: out_gold (\\out_gold), out_gate (\\out_gate) -> out
Found 4 $equiv cells in equiv:
  Of those cells 4 are proven and 0 are unproven.
  Equivalence successfully proven!
"""

UNPROVEN_LOG = """\
  Proof for base case failed. Circuit inherently diverges!
Proved 0 previously unproven $equiv cells.
17. Executing EQUIV_STATUS pass.
Found 1 $equiv cells in equiv:
  Of those cells 0 are proven and 1 are unproven.
  Unproven $equiv $auto$equiv_make.cc:260:find_same_wires$2: \\b_gold \\b_gate
Found a total of 1 unproven $equiv cells.
"""

NO_POINTS_LOG = "Found 0 $equiv cells in equiv:\n"

BMC_FAIL_LOG = """\
Solving problem with 163 variables and 419 clauses..
SAT proof finished - model found: FAIL!

  Time Signal Name             Dec       Hex           Bin
  ---- --------------- ----------- --------- -------------
     1 \\in_a                     0         0             0
     1 \\trigger                  1         1             1

End of script.
"""

BMC_PASS_LOG = "SAT proof finished - no model found: SUCCESS!\n"


class _ScriptedRunner:
    """Returns (or raises) the given outputs in order and records each script."""

    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.scripts: list[str] = []

    def run_script(self, script):
        self.scripts.append(script)
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


def _check(*outputs, golden="g.v", revised="r.v"):
    runner = _ScriptedRunner(*outputs)
    result = LECEngine(runner).run_equivalence_check(golden, revised, "top")
    return result, runner


class TestVerdicts:
    def test_all_points_proven_is_equivalent(self):
        result, runner = _check(PROVEN_LOG)

        assert result.verdict is LECVerdict.EQUIVALENT
        assert result.compare_points == 1
        assert len(runner.scripts) == 1  # no counterexample search needed

    def test_keyword_noise_does_not_flip_verdict(self):
        result, _ = _check(PROVEN_AFTER_RETRIES_LOG)

        assert result.verdict is LECVerdict.EQUIVALENT
        assert result.compare_points == 4

    def test_counterexample_is_nonequivalent(self):
        result, runner = _check(UNPROVEN_LOG, BMC_FAIL_LOG)

        assert result.verdict is LECVerdict.NONEQUIVALENT
        assert result.nonequivalent_points == 1
        assert "\\trigger" in result.counterexample
        assert "End of script" not in result.counterexample
        assert "miter" in runner.scripts[1]

    def test_unproven_without_counterexample_is_abort(self):
        result, _ = _check(UNPROVEN_LOG, BMC_PASS_LOG)

        assert result.verdict is LECVerdict.ABORT
        assert result.abort_points == 1
        assert "Inconclusive" in result.message

    def test_no_compare_points_is_inconclusive(self):
        result, _ = _check(NO_POINTS_LOG)

        assert result.verdict is LECVerdict.INCONCLUSIVE

    def test_missing_status_summary_is_abort(self):
        result, _ = _check("no equiv_status output here\n")

        assert result.verdict is LECVerdict.ABORT

    def test_yosys_error_is_abort_and_keeps_log(self):
        err = YosysError("Yosys execution failed: ERROR: boom", log="full yosys log")

        result, _ = _check(err)

        assert result.verdict is LECVerdict.ABORT
        assert "ERROR: boom" in result.message
        assert result.yosys_log == "full yosys log"

    def test_counterexample_search_error_is_abort(self):
        result, _ = _check(UNPROVEN_LOG, YosysError("Yosys timed out after 5s."))

        assert result.verdict is LECVerdict.ABORT
        assert result.abort_points == 1
        assert "timed out" in result.message


def test_script_quotes_paths_and_isolates_designs():
    _, runner = _check(PROVEN_LOG, golden="my designs/g.v", revised="my designs/r.v")
    script = runner.scripts[0]

    assert 'read_verilog "my designs/g.v"' in script
    assert 'read_verilog "my designs/r.v"' in script
    # Each side is read into its own design, so shared submodule names can't clash.
    assert script.index("design -stash gold") < script.index('read_verilog "my designs/r.v"')
    assert "design -stash gate" in script
    assert "flatten" in script


# ---------------------------------------------------------------- integration
COUNTER = """\
module top(input clk, input rst, output reg [3:0] out);
    always @(posedge clk or posedge rst)
        if (rst) out <= 4'd0;
        else     out <= out + 4'd1;
endmodule
"""


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return str(path)


@requires_yosys
def test_lec_equivalence_identical(tmp_path):
    rtl = _write(tmp_path, "top.v", "module top(input a, output b); assign b = a; endmodule\n")

    result = LECEngine().run_equivalence_check(rtl, rtl, "top")

    assert result.verdict is LECVerdict.EQUIVALENT
    assert result.nonequivalent_points == 0


@requires_yosys
def test_lec_nonequivalent(tmp_path):
    golden = _write(tmp_path, "g.v", "module top(input a, output b); assign b = a; endmodule\n")
    revised = _write(tmp_path, "r.v", "module top(input a, output b); assign b = ~a; endmodule\n")

    result = LECEngine().run_equivalence_check(golden, revised, "top")

    assert result.verdict is LECVerdict.NONEQUIVALENT
    assert result.counterexample


@requires_yosys
def test_lec_sequential_nonequivalent(tmp_path):
    golden = _write(tmp_path, "g.v", COUNTER)
    revised = _write(tmp_path, "r.v", COUNTER.replace("out + 4'd1", "out + 4'd2"))

    result = LECEngine().run_equivalence_check(golden, revised, "top")

    assert result.verdict is LECVerdict.NONEQUIVALENT


@requires_yosys
def test_lec_hierarchical_design(tmp_path):
    rtl = _write(
        tmp_path,
        "hier.v",
        "module leaf(input a, output y); assign y = ~a; endmodule\n"
        "module top(input a, output y); leaf u(.a(a), .y(y)); endmodule\n",
    )

    result = LECEngine().run_equivalence_check(rtl, rtl, "top")

    assert result.verdict is LECVerdict.EQUIVALENT


@requires_yosys
def test_lec_path_with_spaces(tmp_path):
    rtl = _write(tmp_path, "my design/top.v", COUNTER)

    result = LECEngine().run_equivalence_check(rtl, rtl, "top")

    assert result.verdict is LECVerdict.EQUIVALENT
