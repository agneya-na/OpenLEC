"""Yosys-free agent tests. Yosys-dependent engines are replaced with stubs."""
from __future__ import annotations

import openlec.agents.orchestrator as orch_mod
from openlec.agents import BaseAgent
from openlec.agents.optimization_agent import OptimizationAgent
from openlec.agents.parsing_agent import ParsingAgent
from openlec.agents.power_agent import PowerAgent
from openlec.agents.power_intent_agent import PowerIntentAgent
from openlec.agents.reporting_agent import ReportingAgent
from openlec.agents.timing_agent import TimingAgent
from openlec.models.lec_result import LECResult, LECVerdict
from openlec.models.metrics import DesignMetrics
from openlec.models.optimization_step import OptimizationStep, StepVerdict
from openlec.models.schemas import VerificationContext
from openlec.models.upf_models import UPFCheckResult

RTL = "module top(input a, output b); assign b = a; endmodule\n"

GOOD_UPF = """\
set_design_top top
create_power_domain PD_TOP -include_scope
create_power_domain PD_CORE -elements {u_core}
create_supply_net VDD
create_supply_net VSS
set_isolation iso_core -domain PD_CORE -clamp_value 0 \\
    -applies_to outputs -isolation_signal iso_en
set_retention ret_core -domain PD_CORE \\
    -save_signal save_en -restore_signal restore_en
"""

BAD_UPF = """\
set_design_top top
create_power_domain PD_CORE -elements {u_core}
"""


def _ctx(tmp_path, upf_text=None, **overrides):
    rtl = tmp_path / "top.v"
    rtl.write_text(RTL)
    kwargs = {"rtl_file": rtl, "top_module": "top"}
    if upf_text is not None:
        upf = tmp_path / "design.upf"
        upf.write_text(upf_text)
        kwargs["upf_file"] = upf
    kwargs.update(overrides)
    return VerificationContext(**kwargs)


class TestParsingAgent:
    def test_missing_rtl_halts(self, tmp_path):
        ctx = VerificationContext(rtl_file=tmp_path / "nope.v", top_module="top")

        ctx = ParsingAgent().execute(ctx)

        assert ctx.halted is True

    def test_parses_rtl_and_upf(self, tmp_path):
        ctx = _ctx(tmp_path, upf_text=GOOD_UPF)

        ctx = ParsingAgent().execute(ctx)

        assert not ctx.halted
        assert ctx.upf_intent is not None
        assert ctx.golden_netlist == ctx.rtl_file
        assert ctx.revised_netlist == ctx.rtl_file


class TestPowerIntentAgent:
    def test_good_upf_passes(self, tmp_path):
        ctx = _ctx(tmp_path, upf_text=GOOD_UPF)
        ctx = ParsingAgent().execute(ctx)

        ctx = PowerIntentAgent().execute(ctx)

        assert not ctx.halted
        assert all(r.passed for r in ctx.upf_checks.values())

    def test_missing_isolation_halts(self, tmp_path):
        ctx = _ctx(tmp_path, upf_text=BAD_UPF)
        ctx = ParsingAgent().execute(ctx)

        ctx = PowerIntentAgent().execute(ctx)

        assert ctx.halted is True


class TestTimingPowerAgents:
    def test_timing_agent_records_estimate(self, tmp_path):
        agent = TimingAgent()
        agent.estimator = type("Stub", (), {"estimate": lambda s, n, t: 5.0})()

        ctx = TimingAgent.__init__ and _ctx(tmp_path) or None
        ctx = _ctx(tmp_path, delay_budget_ns=10.0)
        ctx = agent.execute(ctx)

        assert ctx.metrics is not None
        assert ctx.metrics.delay_ns == 5.0
        assert not ctx.halted

    def test_power_agent_records_estimate(self, tmp_path):
        agent = PowerAgent()
        agent.estimator = type("Stub", (), {"estimate": lambda s, n, t: 42.0})()

        ctx = _ctx(tmp_path, power_budget_uw=100.0)
        ctx = agent.execute(ctx)

        assert ctx.metrics is not None
        assert ctx.metrics.power_uw == 42.0
        assert not ctx.halted


class TestOptimizationAgent:
    def _stubbed_agent(self, out_path, delay=2.0, power=50.0):
        agent = OptimizationAgent()

        class _Opt:
            def propose(self, iteration):
                return "opt -fast" if iteration == 1 else None

            def apply(self, netlist, pass_cmd, top, iteration, out_dir=None):
                return out_path

        class _Lec:
            def run_equivalence_check(self, g, r, t):
                return LECResult(verdict=LECVerdict.EQUIVALENT, message="stub")

        class _Est:
            def __init__(self, value):
                self.value = value

            def estimate(self, netlist, top):
                return self.value

        agent.optimizer = _Opt()
        agent.lec = _Lec()
        agent.timing = _Est(delay)
        agent.power = _Est(power)
        return agent

    def test_accepts_pass_within_budget(self, tmp_path):
        out = tmp_path / "opt_iter1.v"
        out.write_text(RTL)
        agent = self._stubbed_agent(out)
        ctx = _ctx(tmp_path, iterations=3, delay_budget_ns=10.0,
                   power_budget_uw=100.0)
        ctx.revised_netlist = ctx.rtl_file

        ctx = agent.execute(ctx)

        assert len(ctx.steps) == 1
        assert ctx.steps[0].verdict is StepVerdict.ACCEPT
        assert ctx.revised_netlist == str(out)

    def test_rejects_pass_over_budget(self, tmp_path):
        out = tmp_path / "opt_iter1.v"
        out.write_text(RTL)
        agent = self._stubbed_agent(out, delay=20.0)
        ctx = _ctx(tmp_path, iterations=3, delay_budget_ns=10.0,
                   power_budget_uw=100.0)
        ctx.revised_netlist = ctx.rtl_file

        ctx = agent.execute(ctx)

        assert len(ctx.steps) == 1
        assert ctx.steps[0].verdict is StepVerdict.REJECT
        assert "budget" in ctx.steps[0].reject_reason.lower()
        assert ctx.revised_netlist == ctx.rtl_file


class TestReportingAgent:
    def test_pass_report(self, tmp_path):
        ctx = _ctx(tmp_path)
        ctx.lec_result = LECResult(verdict=LECVerdict.EQUIVALENT, message="ok")
        ctx.upf_checks = {
            "isolation": UPFCheckResult(rule_family="isolation", passed=True),
        }
        ctx.metrics = DesignMetrics(delay_ns=1.0, power_uw=2.0, area_cells=3)

        ctx = ReportingAgent().execute(ctx)

        assert ctx.report is not None
        assert ctx.report.passed is True
        assert "PASS" in ctx.report.to_text()

    def test_halted_context_fails_report(self, tmp_path):
        ctx = _ctx(tmp_path)
        ctx.halt("LEC NONEQUIVALENT: stub")
        ctx.lec_result = LECResult(verdict=LECVerdict.NONEQUIVALENT, message="neq")

        ctx = ReportingAgent().execute(ctx)

        assert ctx.report.passed is False
        assert "FAIL" in ctx.report.to_text()


class _StubBase(BaseAgent):
    def __init__(self, *args, **kwargs):
        pass


class TestOrchestrator:
    def _install_stubs(self, monkeypatch, equiv_verdict=LECVerdict.EQUIVALENT):
        class _Equiv(_StubBase):
            name = "equivalence"

            def execute(self, ctx):
                ctx.lec_result = LECResult(verdict=equiv_verdict, message="stub")
                if equiv_verdict is LECVerdict.NONEQUIVALENT:
                    ctx.halt("LEC NONEQUIVALENT: stub")
                return ctx

        class _Timing(_StubBase):
            name = "timing"

            def execute(self, ctx):
                m = ctx.metrics or DesignMetrics()
                ctx.metrics = DesignMetrics(delay_ns=2.0, power_uw=m.power_uw,
                                            area_cells=m.area_cells)
                return ctx

        class _Power(_StubBase):
            name = "power"

            def execute(self, ctx):
                m = ctx.metrics or DesignMetrics()
                ctx.metrics = DesignMetrics(delay_ns=m.delay_ns, power_uw=50.0,
                                            area_cells=m.area_cells)
                return ctx

        class _Opt(_StubBase):
            name = "optimization"

            def execute(self, ctx):
                ctx.steps.append(OptimizationStep(
                    iteration=1, pass_name="opt -fast",
                    verdict=StepVerdict.ACCEPT,
                    revised_netlist=str(ctx.revised_netlist)))
                return ctx

        monkeypatch.setattr(orch_mod, "EquivalenceAgent", _Equiv)
        monkeypatch.setattr(orch_mod, "TimingAgent", _Timing)
        monkeypatch.setattr(orch_mod, "PowerAgent", _Power)
        monkeypatch.setattr(orch_mod, "OptimizationAgent", _Opt)

    def test_end_to_end_pass(self, tmp_path, monkeypatch):
        self._install_stubs(monkeypatch)
        ctx = _ctx(tmp_path, upf_text=GOOD_UPF, iterations=1)

        report = orch_mod.AgenticOrchestrator(ctx).run_verification_flow()

        assert report.passed is True
        assert len(report.accepted_steps) == 1

    def test_nonequivalent_halts_and_still_reports(self, tmp_path, monkeypatch):
        self._install_stubs(monkeypatch, equiv_verdict=LECVerdict.NONEQUIVALENT)
        ctx = _ctx(tmp_path, upf_text=GOOD_UPF, iterations=1)

        report = orch_mod.AgenticOrchestrator(ctx).run_verification_flow()

        assert report.passed is False
        assert "NONEQUIVALENT" in report.summary