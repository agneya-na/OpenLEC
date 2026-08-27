"""Agentic layer: base class only (submodules imported explicitly to avoid cycles)."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from openlec.models.schemas import VerificationContext

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def execute(self, ctx: VerificationContext) -> VerificationContext:
        """Mutate/extend the shared context and return it."""

    def log(self, ctx: VerificationContext, message: str) -> None:
        logger.info("[%s] %s", self.name, message)
        if ctx.verbose:
            print(f"[{self.name}] {message}")
