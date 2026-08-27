"""
IEEE 1801 UPF Data Models.
Maps to Conformal's internal Power Intent Database after `READ POWER INTENT`.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class AppliesTo(str, Enum):
    INPUTS = "inputs"
    OUTPUTS = "outputs"
    ALL = "all"

class IsolationSense(str, Enum):
    HIGH = "high"
    LOW = "low"

class PowerDomain(BaseModel):
    name: str
    elements: List[str] = Field(default_factory=list)
    include_scope: bool = False

class SupplyNet(BaseModel):
    name: str
    domain: Optional[str] = None
    is_switched: bool = False
    voltage: float = 0.0

class IsolationStrategy(BaseModel):
    name: str
    domain: str
    applies_to: AppliesTo = AppliesTo.OUTPUTS
    clamp_value: str = "0"
    isolation_signal: Optional[str] = None
    isolation_sense: IsolationSense = IsolationSense.HIGH
    location: str = "parent"  # 'parent' or 'self'

class RetentionStrategy(BaseModel):
    name: str
    domain: str
    retention_power_net: Optional[str] = None
    retention_ground_net: Optional[str] = None
    save_signal: Optional[str] = None
    restore_signal: Optional[str] = None

class UPFIntent(BaseModel):
    """Master UPF Intent Object"""
    design_top: str = ""
    power_domains: List[PowerDomain] = Field(default_factory=list)
    supply_nets: List[SupplyNet] = Field(default_factory=list)
    isolation_strategies: List[IsolationStrategy] = Field(default_factory=list)
    retention_strategies: List[RetentionStrategy] = Field(default_factory=list)
    raw_content: str = ""
