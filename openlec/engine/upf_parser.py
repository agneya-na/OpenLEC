import re
from ..models import UPFIntent, PowerDomain, SupplyNet, IsolationRule
import logging

logger = logging.getLogger(__name__)

class UPFParser:
    """Structural parser for IEEE 1801 UPF subsets."""
    
    def parse_file(self, upf_path: str) -> UPFIntent:
        with open(upf_path, 'r') as f:
            content = f.read()
        return self.parse_string(content)

    def parse_string(self, content: str) -> UPFIntent:
        intent = UPFIntent(raw_content=content)
        
        # Parse Power Domains
        for match in re.finditer(r'create_power_domain\s+(\w+)(?:\s+-elements\s+\{([^}]+)\})?', content):
            name = match.group(1)
            elements = match.group(2).split() if match.group(2) else []
            intent.domains.append(PowerDomain(name=name, elements=elements))
            
        # Parse Supply Nets
        for match in re.finditer(r'create_supply_net\s+(\w+)(?:\s+-domain\s+(\w+))?', content):
            intent.supply_nets.append(SupplyNet(name=match.group(1), domain=match.group(2)))
            
        # Parse Isolation Rules
        for match in re.finditer(r'set_isolation\s+(\w+)\s+-domain\s+(\w+).*?-clamp_value\s+(\w+)', content, re.DOTALL):
            intent.isolation_rules.append(IsolationRule(
                name=match.group(1),
                domain=match.group(2),
                clamp_value=match.group(3)
            ))
            
        logger.info(f"Parsed {len(intent.domains)} domains, {len(intent.supply_nets)} nets, {len(intent.isolation_rules)} isolation rules.")
        return intent