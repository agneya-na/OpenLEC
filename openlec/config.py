"""Configuration loading (YAML file + CLI overrides)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel

from openlec.models.schemas import VerificationContext


class OpenLECConfig(BaseModel):
    rtl_file: str
    top_module: str
    upf_file: Optional[str] = None
    iterations: int = 3
    delay_budget_ns: float = 10.0
    power_budget_uw: float = 1000.0
    verbose: bool = False
    yosys_exec: str = "yosys"

    def to_context(self) -> VerificationContext:
        return VerificationContext(
            rtl_file=Path(self.rtl_file),
            top_module=self.top_module,
            upf_file=Path(self.upf_file) if self.upf_file else None,
            iterations=self.iterations,
            delay_budget_ns=self.delay_budget_ns,
            power_budget_uw=self.power_budget_uw,
            verbose=self.verbose,
        )


def load_config_file(path: Optional[Path]) -> Dict[str, Any]:
    if path is None or not Path(path).exists():
        return {}
    data = yaml.safe_load(Path(path).read_text()) or {}
    return data.get("openlec", {}) or {}
