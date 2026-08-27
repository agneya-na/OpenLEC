import re
from pathlib import Path
from ..models.upf_models import UPFIntent, PowerDomain, IsolationStrategy, RetentionStrategy

class UPFParser:
    """
    Parses IEEE 1801 UPF files. 
    Equivalent to Conformal's `READ POWER INTENT` command.
    """
    def __init__(self, upf_file: str):
        self.upf_file = Path(upf_file)
        self.intent = UPFIntent(design_top="")
        
    def parse(self) -> UPFIntent:
        content = self.upf_file.read_text()
        content = re.sub(r'#.*', '', content) # Remove comments
        
        self._parse_set_design_top(content)
        self._parse_power_domains(content)
        self._parse_isolation(content)
        self._parse_retention(content)
        return self.intent

    def _parse_set_design_top(self, content: str):
        match = re.search(r'set_design_top\s+([a-zA-Z0-9_\/]+)', content)
        if match:
            self.intent.design_top = match.group(1).split('/')[-1]

    def _parse_power_domains(self, content: str):
        # Regex for: create_power_domain PD1 -elements {inst1 inst2}
        pattern = r'create_power_domain\s+([a-zA-Z0-9_]+)\s*(?:-elements\s+\{([^}]+)\})?\s*(?:-include_scope)?'
        for match in re.finditer(pattern, content):
            name = match.group(1)
            elements = match.group(2).split() if match.group(2) else []
            self.intent.power_domains.append(PowerDomain(name=name, elements=elements))

    def _parse_isolation(self, content: str):
        # Regex for: set_isolation ISO1 -domain PD1 -applies_to outputs -clamp_value 0 -isolation_signal iso_en
        pattern = r'set_isolation\s+([a-zA-Z0-9_]+)\s+-domain\s+([a-zA-Z0-9_]+)\s+-applies_to\s+([a-zA-Z]+)\s+-clamp_value\s+([01])\s+(?:-isolation_signal\s+([a-zA-Z0-9_]+))?'
        for match in re.finditer(pattern, content):
            self.intent.isolation_strategies.append(IsolationStrategy(
                name=match.group(1), domain=match.group(2), applies_to=match.group(3),
                clamp_value=match.group(4), isolation_signal=match.group(5)
            ))

    def _parse_retention(self, content: str):
        pattern = r'set_retention\s+([a-zA-Z0-9_]+)\s+-domain\s+([a-zA-Z0-9_]+).*?(?:-save_signal\s+\{([a-zA-Z0-9_]+)\})?.*?(?:-restore_signal\s+\{([a-zA-Z0-9_]+)\})?'
        for match in re.finditer(pattern, content, re.DOTALL):
            self.intent.retention_strategies.append(RetentionStrategy(
                name=match.group(1), domain=match.group(2),
                save_signal=match.group(3), restore_signal=match.group(4)
            ))
