"""CLI tests. Unit tests stub the orchestrator; integration tests need Yosys."""
from __future__ import annotations

import shutil

import pytest

from openlec import cli
from openlec.config import load_config_file
from openlec.engine.yosys_runner import YosysRunner, quote_path
from openlec.models.lec_result import LECResult, LECVerdict
from openlec.models.schemas import VerificationReport

RTL = "module top(input a, output b); assign b = a; endmodule\n"

requires_yosys = pytest.mark.skipif(
    shutil.which("yosys") is None,
    reason="Yosys not installed; skipping CLI integration tests.",
)


class _FakeOrchestrator:
    last_ctx = None

    def __init__(self, ctx, runner=None):
        self.ctx = ctx
        _FakeOrchestrator.last_ctx = ctx

    def run_verification_flow(self):
        passed = self.ctx.top_module == "good"
        return VerificationReport(
            passed=passed,
            summary="stubbed",
            lec_result=LECResult(verdict=LECVerdict.EQUIVALENT),
        )


def _rtl(tmp_path, name="top.v", text=RTL):
    path = tmp_path / name
    path.write_text(text)
    return path


def test_help_exits_zero():
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0


def test_missing_rtl_returns_usage_error(tmp_path, capsys):
    assert cli.main([str(tmp_path / "nope.v"), "--top", "top"]) == 2
    assert "RTL file not found" in capsys.readouterr().err


def test_missing_revised_returns_usage_error(tmp_path, capsys):
    rtl = _rtl(tmp_path)

    rc = cli.main([str(rtl), "--revised", str(tmp_path / "nope_syn.v"), "--top", "top"])

    assert rc == 2
    assert "revised file not found" in capsys.readouterr().err


def test_revised_is_passed_to_context(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "AgenticOrchestrator", _FakeOrchestrator)
    rtl = _rtl(tmp_path)
    syn = _rtl(tmp_path, "top_syn.v")

    cli.main([str(rtl), "--revised", str(syn), "--top", "good"])

    assert _FakeOrchestrator.last_ctx.rtl_file == rtl
    assert _FakeOrchestrator.last_ctx.revised_file == syn


def test_revised_defaults_to_none(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "AgenticOrchestrator", _FakeOrchestrator)

    cli.main([str(_rtl(tmp_path)), "--top", "good"])

    assert _FakeOrchestrator.last_ctx.revised_file is None


def test_revised_from_config_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "AgenticOrchestrator", _FakeOrchestrator)
    syn = _rtl(tmp_path, "top_syn.v")
    cfg = tmp_path / "openlec.yaml"
    cfg.write_text(f"openlec:\n  revised_file: '{syn.as_posix()}'\n")

    cli.main([str(_rtl(tmp_path)), "--top", "good", "--config", str(cfg)])

    assert _FakeOrchestrator.last_ctx.revised_file.resolve() == syn.resolve()


def test_exit_zero_on_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "AgenticOrchestrator", _FakeOrchestrator)

    rc = cli.main([str(_rtl(tmp_path)), "--top", "good"])

    assert rc == 0


def test_exit_one_on_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "AgenticOrchestrator", _FakeOrchestrator)

    rc = cli.main([str(_rtl(tmp_path)), "--top", "bad"])

    assert rc == 1


def test_load_config_file(tmp_path):
    cfg = tmp_path / "openlec.yaml"
    cfg.write_text("openlec:\n  yosys_path: /usr/bin/yosys\n  iterations: 7\n")

    data = load_config_file(cfg)

    assert data["yosys_path"] == "/usr/bin/yosys"
    assert load_config_file(None) == {}
    assert load_config_file(tmp_path / "missing.yaml") == {}


# ---------------------------------------------------------------- integration
COUNTER = """\
module counter(input clk, input rst, output reg [3:0] out);
    always @(posedge clk or posedge rst)
        if (rst) out <= 4'd0;
        else     out <= out + 4'd1;
endmodule
"""


def _synthesize(src, out):
    YosysRunner().run_script(
        f"read_verilog {quote_path(src)}\nsynth -top counter\n"
        f"write_verilog -noattr {quote_path(out)}\n"
    )


@requires_yosys
def test_rtl_vs_synthesized_netlist_passes(tmp_path, capsys):
    rtl = _rtl(tmp_path, "counter.v", COUNTER)
    gates = tmp_path / "counter_syn.v"
    _synthesize(rtl, gates)

    rc = cli.main([str(rtl), "--revised", str(gates), "--top", "counter", "--iterations", "0"])

    out = capsys.readouterr().out
    assert rc == 0, out
    assert "LEC    : Equivalent" in out
    assert f"Revised: {gates}" in out


@requires_yosys
def test_buggy_synthesized_netlist_fails_with_counterexample(tmp_path, capsys):
    rtl = _rtl(tmp_path, "counter.v", COUNTER)
    buggy = _rtl(tmp_path, "counter_bug.v", COUNTER.replace("out + 4'd1", "out + 4'd2"))
    gates = tmp_path / "counter_bug_syn.v"
    _synthesize(buggy, gates)

    rc = cli.main([str(rtl), "--revised", str(gates), "--top", "counter", "--iterations", "0"])

    out = capsys.readouterr().out
    assert rc == 1
    assert "LEC NONEQUIVALENT" in out
    assert "Counterexample:" in out
