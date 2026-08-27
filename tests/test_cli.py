"""CLI tests (Yosys-free; orchestrator is stubbed)."""
from __future__ import annotations

import pytest

from openlec import cli
from openlec.config import load_config_file
from openlec.models.lec_result import LECResult, LECVerdict
from openlec.models.schemas import VerificationReport

RTL = "module top(input a, output b); assign b = a; endmodule\n"


class _FakeOrchestrator:
    def __init__(self, ctx, runner=None):
        self.ctx = ctx

    def run_verification_flow(self):
        passed = self.ctx.top_module == "good"
        return VerificationReport(
            passed=passed,
            summary="stubbed",
            lec_result=LECResult(verdict=LECVerdict.EQUIVALENT),
        )


def test_help_exits_zero():
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0


def test_missing_rtl_returns_usage_error(tmp_path):
    assert cli.main([str(tmp_path / "nope.v"), "--top", "top"]) == 2


def test_exit_zero_on_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "AgenticOrchestrator", _FakeOrchestrator)
    rtl = tmp_path / "top.v"
    rtl.write_text(RTL)

    rc = cli.main([str(rtl), "--top", "good"])

    assert rc == 0


def test_exit_one_on_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "AgenticOrchestrator", _FakeOrchestrator)
    rtl = tmp_path / "top.v"
    rtl.write_text(RTL)

    rc = cli.main([str(rtl), "--top", "bad"])

    assert rc == 1


def test_load_config_file(tmp_path):
    cfg = tmp_path / "openlec.yaml"
    cfg.write_text("openlec:\n  yosys_path: /usr/bin/yosys\n  iterations: 7\n")

    data = load_config_file(cfg)

    assert data["yosys_path"] == "/usr/bin/yosys"
    assert load_config_file(None) == {}
    assert load_config_file(tmp_path / "missing.yaml") == {}