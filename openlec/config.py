# 📄 openlec/config.py
from pydantic import BaseModel, Field
from typing import Optional

class OpenLECConfig(BaseModel):
    rtl_file: str
    upf_file: Optional[str] = None
    top_module: str
    iterations: int = Field(default=5, description="Max optimization iterations")
    delay_budget_ns: float = Field(default=10.0)
    power_budget_mw: float = Field(default=1000.0)
    verbose: bool = False
    yosys_exec: str = "yosys"
