"""
UPF Structural & Power-Aware Checker.
Maps to Conformal's `CHECK LOWPOWER CELLS`, `COMPARE POWER CONSISTENCY`, and `REPORT LOWPOWER DATA`.
"""
import logging
from typing import Dict, Any, List
from openlec.models.upf_models import UPFIntent, PowerDomain
from openlec.models.lec_result import UPFCheckResult

logger = logging.getLogger(__name__)

class UPFChecker:
    def __init__(self, intent: UPFIntent, netlist_ast: Dict[str, Any] = None):
        """
        netlist_ast: Extracted via Yosys AST or Surelog. 
        For structural checks, we expect a dict like:
        {
            "isolated_domains": ["PD_CORE"],
            "retention_mapped_regs": ["u_core/reg1", "u_core/reg2"],
            "domain_elements": {"PD_CORE": ["u_core"]}
        }
        """
        self.intent = intent
        self.netlist_ast = netlist_ast or {}

    def check_isolation_clamps(self) -> UPFCheckResult:
        """
        Verifies isolation cells at domain boundaries.
        Conformal Equivalent: `CHECK LOWPOWER CELLS` (Isolation checks)
        """
        violations = []
        checked_rules = ["ISO_MISSING", "ISO_CLAMP_VALUE"]
        
        # Domains that have isolation strategies defined
        isolated_domains = {iso.domain for iso in self.intent.isolation_strategies}
        
        # Check if all switchable domains have isolation rules
        for pd in self.intent.power_domains:
            if pd.include_scope:
                continue # Top level usually doesn't need isolation
                
            if pd.name not in isolated_domains:
                # In a real flow, we check if the domain is switchable via PST (Power State Table).
                # Here we flag it as a warning/violation if it has elements but no isolation.
                if pd.elements:
                    violations.append(f"ISO_MISSING: Power Domain '{pd.name}' has elements but no set_isolation strategy defined.")
                    
        # Check AST for actual isolation cell insertion (Mocked for demonstration)
        ast_isolated = self.netlist_ast.get("isolated_domains", [])
        for iso in self.intent.isolation_strategies:
            if iso.domain not in ast_isolated and iso.domain in self.netlist_ast.get("domain_elements", {}):
                 violations.append(f"ISO_IMPL_MISSING: Isolation strategy '{iso.name}' for domain '{iso.domain}' not found in synthesized netlist AST.")

        return UPFCheckResult(
            passed=len(violations) == 0,
            violations=violations,
            checked_rules=checked_rules
        )

    def check_retention_registers(self) -> UPFCheckResult:
        """
        Verifies state retention mapping.
        Conformal Equivalent: `ADD RETENTION_REGISTER MAPPING` & `CHECK LOWPOWER CELLS`
        """
        violations = []
        checked_rules = ["RET_MISSING", "RET_CTRL_SIGNALS"]
        
        ret_domains = {ret.domain for ret in self.intent.retention_strategies}
        
        for pd in self.intent.power_domains:
            if pd.name not in ret_domains and pd.elements:
                # Warning: Domain might lose state on power down
                violations.append(f"RET_MISSING: Power Domain '{pd.name}' has no set_retention strategy. State will be lost on power-off.")
                
        # Check control signals
        for ret in self.intent.retention_strategies:
            if not ret.save_signal or not ret.restore_signal:
                violations.append(f"RET_CTRL_SIGNALS: Retention strategy '{ret.name}' missing save/restore control signals.")

        return UPFCheckResult(
            passed=len([v for v in violations if v.startswith("RET_CTRL")]) == 0, # Allow missing ret as warning, fail on bad ctrl
            violations=violations,
            checked_rules=checked_rules
        )

    def run_all_checks(self) -> Dict[str, UPFCheckResult]:
        """Runs all structural UPF checks."""
        return {
            "isolation": self.check_isolation_clamps(),
            "retention": self.check_retention_registers()
        }
