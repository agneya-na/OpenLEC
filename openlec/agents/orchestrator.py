"""Multi-agent orchestration loop (replaces manual Conformal dofile scripting)."""
from __future__ import annotations

import logging
from typing import List, Optional

from openlec.agents import BaseAgent
from openlec.agents.equivalence_agent import EquivalenceAgent
from openlec.agents.optimization_agent import OptimizationAgent
from openlec.agents.parsing_agent import ParsingAgent
from openlec.agents.power_agent import PowerAgent
from openlec.agents.power_intent_agent import PowerIntentAgent
from openlec.agents.reporting_agent import ReportingAgent
from openlec.agents.timing_agent import TimingAgent
from openlec.engine.yosys_runner import YosysRunner
from openlec.models.schemas import VerificationContext, VerificationReport

logger = logging.getLogger(__name__)


class AgenticOrchestrator:
    def __init__(self, ctx: VerificationContext, runner: Optional[YosysRunner] = None) -> None:
        self.ctx = ctx
        self.runner = runner or YosysRunner()
        self.agents: List[BaseAgent] = [
            ParsingAgent(),
            PowerIntentAgent(),
            EquivalenceAgent(self.runner),
            TimingAgent(self.runner),
            PowerAgent(self.runner),
            OptimizationAgent(self.runner),
            ReportingAgent(),
        ]

    def run_verification_flow(self) -> VerificationReport:
        for agent in self.agents:
            logger.info("Running agent: %s", agent.name)
            self.ctx = agent.execute(self.ctx)
            if self.ctx.halted and not isinstance(agent, ReportingAgent):
                ReportingAgent().execute(self.ctx)  # always emit a report
                break
        assert self.ctx.report is not None
        return self.ctx.report
