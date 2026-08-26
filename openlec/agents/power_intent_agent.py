from . import BaseAgent
from ..engine.upf_parser import UPFParser
from ..engine.upf_checker import UPFChecker
from ..models import Verdict
from typing import Dict, Any

class PowerIntentAgent(BaseAgent):
    def __init__(self):
        self.parser = UPFParser()
        self.checker = UPFChecker()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        upf_file = context.get("upf_file")
        if not upf_file:
            context["halt"] = True
            context["reason"] = "Missing UPF file."
            return context

        intent = self.parser.parse_file(upf_file)
        context["upf_intent"] = intent
        
        verdict = self.checker.check_isolation_clamps(intent)
        context["upf_verdict"] = verdict
        
        if verdict == Verdict.FAIL:
            context["halt"] = True
            context["reason"] = "UPF Structural Check Failed: Missing isolation rules."
            
        return context