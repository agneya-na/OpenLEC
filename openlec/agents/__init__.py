from abc import ABC, abstractmethod
from typing import Dict, Any
from ..models import Verdict

class BaseAgent(ABC):
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        pass

class Orchestrator:
    def __init__(self, agents: list[BaseAgent]):
        self.agents = agents

    def run(self, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        context = initial_context
        for agent in self.agents:
            agent_name = agent.__class__.__name__
            print(f"🤖 Running Agent: {agent_name}")
            context = agent.execute(context)
            if context.get("halt"):
                print(f"🛑 Orchestrator halted by {agent_name}: {context.get('reason')}")
                break
        return context