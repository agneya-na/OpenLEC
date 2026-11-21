"""
LEC Result Models.
Maps to Conformal's `COMPARE` and `REPORT COMPARE DATA` outputs.
"""
from enum import Enum

from pydantic import BaseModel


class LECVerdict(str, Enum):
    EQUIVALENT = "Equivalent"       # Conformal: EQ - every compare point proven
    NONEQUIVALENT = "Nonequivalent" # Conformal: NEQ - a concrete counterexample was found
    ABORT = "Abort"                 # Conformal: Abort - setup error, timeout, or unproven
                                    # points with no counterexample within the bound
    INCONCLUSIVE = "Inconclusive"   # nothing to compare (no matching compare points)

class LECResult(BaseModel):
    verdict: LECVerdict
    message: str = ""
    compare_points: int = 0
    unmapped_points: int = 0
    abort_points: int = 0
    nonequivalent_points: int = 0
    counterexample: str = ""
    yosys_log: str = ""
