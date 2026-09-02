"""
LEC Result Models.
Maps to Conformal's `COMPARE` and `REPORT COMPARE DATA` outputs.
"""
from enum import Enum

from pydantic import BaseModel


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
