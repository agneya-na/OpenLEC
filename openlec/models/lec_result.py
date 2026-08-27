from enum import Enum
from pydantic import BaseModel

class LECVerdict(Enum):
    EQUIVALENT = "Equivalent"       # Conformal: EQ
    NONEQUIVALENT = "Nonequivalent" # Conformal: NEQ
    ABORT = "Abort"                 # Conformal: Abort (SAT timeout/inconclusive)

class LECResult(BaseModel):
    verdict: LECVerdict
    message: str
    unmapped_points: int = 0
    abort_points: int = 0
