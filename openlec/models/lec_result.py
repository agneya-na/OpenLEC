"""
LEC Result Models.
Maps to Conformal's `COMPARE` and `REPORT COMPARE DATA` outputs.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class LECVerdict(str, Enum):
    EQUIVALENT = "Equivalent"       # Conformal: EQ
    NONEQUIVALENT = "Nonequivalent" # Conformal: NEQ
    ABORT = "Abort"                 # Conformal: Abort (SAT timeout/inconclusive)
    INCONCLUSIVE = "Inconclusive"

class LECResult(BaseModel):
    verdict: LECVerdict
    message: str = ""
    unmapped_points: int = 0
    abort_points: int = 0
    nonequivalent_points: int = 0
    yosys_log: str = ""
    
class UPFCheckResult(BaseModel):
    passed: bool
    violations: List[str] = Field(default_factory=list)
    checked_rules: List[str] = Field(default_factory=list)
