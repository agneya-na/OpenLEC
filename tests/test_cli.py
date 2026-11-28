"""CLI tests. Unit tests stub the orchestrator; integration tests need Yosys."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from openlec import cli
from openlec.config import load_config_file
from openlec.engine.design_source import DesignSource, parse_filelist
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
    path.parent.mkdir(parents=True, exist_ok=True)
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


def test_single_plain_file_keeps_path_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "AgenticOrchestrator", _FakeOrchestrator)

    cli.main([str(_rtl(tmp_path)), "--top", "good"])

    assert _FakeOrchestrator.last_ctx.golden_source is None
    assert _FakeOrchestrator.last_ctx.revised_source is None


def test_multiple_files_and_shared_options_build_golden_source(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "AgenticOrchestrator", _FakeOrchestrator)
    a, b = _rtl(tmp_path, "a.v"), _rtl(tmp_path, "b.v")
    (tmp_path / "inc").mkdir()

    cli.main([str(a), str(b), "-I", str(tmp_path / "inc"), "-D", "W=8", "--sv", "--top", "good"])

    src = _FakeOrchestrator.last_ctx.golden_source
    assert src.files == (a, b)
    assert src.include_dirs == (tmp_path / "inc",)
    assert src.defines == (("W", "8"),)
    assert src.sv is True
    assert _FakeOrchestrator.last_ctx.rtl_file == a


def test_filelists_build_golden_and_revised_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "AgenticOrchestrator", _FakeOrchestrator)
    _rtl(tmp_path, "g/rtl/top.sv")
    (tmp_path / "g" / "inc").mkdir()
    golden_f = _rtl(tmp_path, "g/golden.f", "+incdir+inc\n+define+W=4\nrtl/top.sv\n")
    syn = _rtl(tmp_path, "r/top_syn.v")
    revised_f = _rtl(tmp_path, "r/revised.f", "top_syn.v\n")

    rc = cli.main(["-F", str(golden_f), "--revised-F", str(revised_f), "-D", "W=8",
                   "--top", "good"])

    ctx = _FakeOrchestrator.last_ctx
    assert rc == 0
    assert ctx.golden_source.files == (tmp_path / "g" / "rtl" / "top.sv",)
    assert ctx.golden_source.include_dirs == (tmp_path / "g" / "inc",)
    assert ctx.golden_source.defines == (("W", "8"),)  # -D overrides the list's +define+
    assert ctx.revised_source.files == (syn,)
    assert ctx.revised_source.defines == (("W", "8"),)  # shared -D applies to both sides
    assert ctx.revised_file == syn


def test_missing_filelist_returns_usage_error(tmp_path, capsys):
    assert cli.main(["-F", str(tmp_path / "nope.f"), "--top", "top"]) == 2
    assert "Cannot read file list" in capsys.readouterr().err


def test_missing_file_inside_filelist_returns_usage_error(tmp_path, capsys):
    lst = _rtl(tmp_path, "top.f", "gone.v\n")

    assert cli.main(["-F", str(lst), "--top", "top"]) == 2
    assert "RTL file not found" in capsys.readouterr().err


def test_no_golden_files_returns_usage_error(capsys):
    assert cli.main(["--top", "top"]) == 2
    assert "no golden design files" in capsys.readouterr().err


def test_bad_define_returns_usage_error(tmp_path, capsys):
    assert cli.main([str(_rtl(tmp_path)), "-D", "1BAD", "--top", "top"]) == 2
    assert "Invalid macro name" in capsys.readouterr().err


def test_unsupported_filelist_option_warns(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "AgenticOrchestrator", _FakeOrchestrator)
    _rtl(tmp_path, "a.v")
    lst = _rtl(tmp_path, "top.f", "+libext+.v\na.v\n")

    cli.main(["-F", str(lst), "--top", "good"])

    assert "ignoring unsupported option '+libext+.v'" in capsys.readouterr().err


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


SV_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "designs" / "sv"


@requires_yosys
def test_sv_filelist_vs_synthesized_netlist_passes(tmp_path, capsys):
    shutil.copytree(SV_EXAMPLE, tmp_path / "sv")
    filelist = tmp_path / "sv" / "accum_top.f"
    fl = parse_filelist(filelist, relative_to_list=True)
    gates = tmp_path / "accum_top_syn.v"
    YosysRunner().run_script(
        DesignSource.from_paths(fl.files, fl.include_dirs).read_script()
        + f"synth -top accum_top\nwrite_verilog -noattr {quote_path(gates)}\n"
    )

    rc = cli.main(["-F", str(filelist), "--revised", str(gates), "--top", "accum_top",
                   "--iterations", "0"])

    out = capsys.readouterr().out
    assert rc == 0, out
    assert "LEC    : Equivalent" in out
    assert "accum_core.sv" in out  # report lists the golden files
