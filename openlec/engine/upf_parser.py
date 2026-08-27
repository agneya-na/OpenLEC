"""
UPF Parser Engine.
Equivalent to Conformal's `READ POWER INTENT` command.
Parses IEEE 1801 UPF files into structured Pydantic models.
"""
import re
import logging
from pathlib import Path
from typing import List
from openlec.models.upf_models import (
    UPFIntent, PowerDomain, SupplyNet, IsolationStrategy, RetentionStrategy, AppliesTo, IsolationSense
)

logger = logging.getLogger(__name__)

class UPFParser:
    def __init__(self, upf_file: str | Path):
        self.upf_file = Path(upf_file)
        if not self.upf_file.exists():
            raise FileNotFoundError(f"UPF file not found: {self.upf_file}")

    def parse(self) -> UPFIntent:
        content = self.upf_file.read_text()
        # Remove single-line comments
        content = re.sub(r'#.*', '', content)
        
        intent = UPFIntent(raw_content=content)
        
        # 1. Parse Design Top
        top_match = re.search(r'set_design_top\s+([a-zA-Z0-9_\/]+)', content)
        if top_match:
            intent.design_top = top_match.group(1)
            
        # 2. Parse Power Domains
        # Regex handles: create_power_domain PD1 -elements {inst1 inst2} -include_scope
        pd_pattern = r'create_power_domain\s+([a-zA-Z0-9_]+)\s*(?:-elements\s+\{([^}]*)\})?\s*(?:-include_scope)?'
        for match in re.finditer(pd_pattern, content):
            name = match.group(1)
            elements_str = match.group(2)
            elements = elements_str.split() if elements_str else []
            include_scope = "-include_scope" in match.group(0)
            intent.power_domains.append(PowerDomain(name=name, elements=elements, include_scope=include_scope))
            
        # 3. Parse Supply Nets
        sn_pattern = r'create_supply_net\s+([a-zA-Z0-9_]+)(?:\s+-domain\s+([a-zA-Z0-9_]+))?'
        for match in re.finditer(sn_pattern, content):
            intent.supply_nets.append(SupplyNet(name=match.group(1), domain=match.group(2)))
            
        # 4. Parse Isolation Strategies
        # set_isolation ISO1 -domain PD1 -applies_to outputs -clamp_value 0 -isolation_signal iso_en -isolation_sense high
        iso_pattern = r'set_isolation\s+([a-zA-Z0-9_]+)\s+-domain\s+([a-zA-Z0-9_]+)\s+(?:-applies_to\s+([a-zA-Z]+))?\s+(?:-clamp_value\s+([01xXzZ]))?\s+(?:-isolation_signal\s+([a-zA-Z0-9_]+))?\s+(?:-isolation_sense\s+([a-zA-Z]+))?\s+(?:-location\s+([a-zA-Z]+))?'
        for match in re.finditer(iso_pattern, content):
            intent.isolation_strategies.append(IsolationStrategy(
                name=match.group(1),
                domain=match.group(2),
                applies_to=AppliesTo(match.group(3) or "outputs"),
                clamp_value=match.group(4) or "0",
                isolation_signal=match.group(5),
                isolation_sense=IsolationSense(match.group(6) or "high"),
                location=match.group(7) or "parent"
            ))
            
        # 5. Parse Retention Strategies
        # set_retention RET1 -domain PD1 -retention_power_net VDD -save_signal save_en -restore_signal restore_en
        ret_pattern = r'set_retention\s+([a-zA-Z0-9_]+)\s+-domain\s+([a-zA-Z0-9_]+)(?:\s+-retention_power_net\s+([a-zA-Z0-9_]+))?(?:\s+-retention_ground_net\s+([a-zA-Z0-9_]+))?(?:\s+-save_signal\s+\{?([a-zA-Z0-9_]+)\}?)?(?:\s+-restore_signal\s+\{?([a-zA-Z0-9_]+)\}?)?'
        for match in re.finditer(ret_pattern, content):
            intent.retention_strategies.append(RetentionStrategy(
                name=match.group(1),
                domain=match.group(2),
                retention_power_net=match.group(3),
                retention_ground_net=match.group(4),
                save_signal=match.group(5),
                restore_signal=match.group(6)
            ))
            
        logger.info(f"Parsed UPF: {len(intent.power_domains)} Domains, {len(intent.isolation_strategies)} Isolation Rules, {len(intent.retention_strategies)} Retention Rules.")
        return intent
