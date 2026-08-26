from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

class Verdict(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    ERROR = "ERROR"

@dataclass
class LECResult:
    equivalent: bool
    yosys_log: str
    abort_points: int = 0
    nonequivalent_points: int = 0

@dataclass
class PowerDomain:
    name: str
    elements: List[str] = field(default_factory=list)

@dataclass
class SupplyNet:
    name: str
    domain: Optional[str] = None

@dataclass
class IsolationRule:
    name: str
    domain: str
    clamp_value: str = "0"

@dataclass
class UPFIntent:
    domains: List[PowerDomain] = field(default_factory=list)
    supply_nets: List[SupplyNet] = field(default_factory=list)
    isolation_rules: List[IsolationRule] = field(default_factory=list)
    raw_content: str = ""

@dataclass
class Metrics:
    delay_ns: float = 0.0
    power_mw: float = 0.0
    area_um2: float = 0.0

@dataclass
class OptimizationStep:
    pass_name: str
    verdict: Verdict
    metrics: Metrics
    lec_result: Optional[LECResult] = None
    reason: str = ""