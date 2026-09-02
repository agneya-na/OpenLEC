"""
IEEE 1801 UPF Data Models.
Maps to Conformal's internal Power Intent Database after `READ POWER INTENT`.
"""
from enum import Enum

from pydantic import BaseModel, Field


class AppliesTo(str, Enum):
    INPUTS = "inputs"
    OUTPUTS = "outputs"
    ALL = "all"

class IsolationSense(str, Enum):
    HIGH = "high"
    LOW = "low"

class SupplyState(str, Enum):
    ON = "on"
    OFF = "off"
    RETENTION = "retention"

class PowerDomain(BaseModel):
    name: str
    elements: list[str] = Field(default_factory=list)
    include_scope: bool = False

class SupplyNet(BaseModel):
    name: str
    domain: str | None = None
    is_switched: bool = False
    voltage: float = 0.0

class IsolationStrategy(BaseModel):
    name: str
    domain: str
    applies_to: AppliesTo = AppliesTo.OUTPUTS
    clamp_value: str = "0"
    isolation_signal: str | None = None
    isolation_sense: IsolationSense = IsolationSense.HIGH
    location: str = "parent"  # 'parent' or 'self'

class RetentionStrategy(BaseModel):
    name: str
    domain: str
    retention_power_net: str | None = None
    retention_ground_net: str | None = None
    save_signal: str | None = None
    restore_signal: str | None = None

class UPFIntent(BaseModel):
    """Master UPF Intent Object"""
    design_top: str = ""
    power_domains: list[PowerDomain] = Field(default_factory=list)
    supply_nets: list[SupplyNet] = Field(default_factory=list)
    isolation_strategies: list[IsolationStrategy] = Field(default_factory=list)
    retention_strategies: list[RetentionStrategy] = Field(default_factory=list)
    raw_content: str = ""

    def domain_names(self) -> list[str]:
        return [pd.name for pd in self.power_domains]

    def isolated_domains(self) -> set[str]:
        return {iso.domain for iso in self.isolation_strategies}

    def retained_domains(self) -> set[str]:
        return {ret.domain for ret in self.retention_strategies}


class UPFCheckResult(BaseModel):
    rule_family: str = ""
    passed: bool
    violations: list[str] = Field(default_factory=list)
    checked_rules: list[str] = Field(default_factory=list)
