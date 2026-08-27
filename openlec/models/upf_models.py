from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum

class SupplyState(Enum):
    ON = "ON"
    OFF = "OFF"

class PowerDomain(BaseModel):
    name: str
    elements: List[str] = Field(default_factory=list)
    include_scope: bool = False

class IsolationStrategy(BaseModel):
    name: str
    domain: str
    applies_to: str = "outputs" # inputs, outputs, all
    clamp_value: str = "0"
    isolation_signal: Optional[str] = None
    location: str = "parent"

class RetentionStrategy(BaseModel):
    name: str
    domain: str
    retention_power_net: Optional[str] = None
    save_signal: Optional[str] = None
    restore_signal: Optional[str] = None

class UPFIntent(BaseModel):
    """Maps to Conformal's internal Power Intent Database after READ POWER INTENT"""
    design_top: str
    power_domains: List[PowerDomain] = Field(default_factory=list)
    isolation_strategies: List[IsolationStrategy] = Field(default_factory=list)
    retention_strategies: List[RetentionStrategy] = Field(default_factory=list)
