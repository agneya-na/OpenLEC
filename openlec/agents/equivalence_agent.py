from . import BaseAgent
from ..engine.lec_engine import LECEngine
from ..engine.yosys_runner import YosysRunner
from ..models import Verdict
from typing import Dict, Any

class EquivalenceAgent(BaseAgent):
    def __init__(self):
        self.lec_engine = LECEngine(YosysRunner())

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        golden = context.get("golden_rtl")
        revised = context.get("revised_rtl")
        top = context.get("top_module")
        
        if not all([golden, revised, top]):
            context["halt"] = True
            context["reason"] = "Missing RTL files for LEC."
            return context

        result = self.lec_engine.check_equivalence(golden, revised, top)
        context["lec_result"] = result
        
        if not result.equivalent:
            context["verdict"] = Verdict.FAIL
            context["halt"] = True
            context["reason"] = f"LEC Failed: {result.nonequivalent_points} unproven points."
        else:
            context["verdict"] = Verdict.PASS
            
        return context