"""
UPF Structural & Power-Aware Checker.
Maps to Conformal's `CHECK LOWPOWER CELLS`, `COMPARE POWER CONSISTENCY`, and `REPORT LOWPOWER DATA`.
"""
import logging
from typing import Any

from openlec.models.upf_models import UPFCheckResult, UPFIntent

logger = logging.getLogger(__name__)

class UPFChecker:
    def __init__(self, intent: UPFIntent, netlist_ast: dict[str, Any] | None = None):
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
        checked_rules = ["ISO_MISSING", "ISO_NOT_IMPLEMENTED"]
        
        # Domains that have isolation strategies defined
        isolated_domains = {iso.domain for iso in self.intent.isolation_strategies}
        
        # Check if all switchable domains have isolation rules
        for pd in self.intent.power_domains:
            if pd.include_scope:
                continue
                
            if pd.name not in isolated_domains and pd.elements:
                violations.append(
                    f"ISO_MISSING: Power Domain '{pd.name}' has elements but no set_isolation strategy defined."
                )

        ast_isolated = self.netlist_ast.get("isolated_domains", [])
        for iso in self.intent.isolation_strategies:
            if (
                iso.domain not in ast_isolated
                and iso.domain in self.netlist_ast.get("domain_elements", {})
            ):
                violations.append(
                    f"ISO_NOT_IMPLEMENTED: Isolation strategy '{iso.name}' for domain '{iso.domain}' not found in synthesized netlist AST."
                )

        return UPFCheckResult(
            rule_family="isolation",
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
        checked_rules = ["RET_CONTROL", "RET_DOMAIN"]

        known_domains = {pd.name for pd in self.intent.power_domains}
        for ret in self.intent.retention_strategies:
            if ret.domain not in known_domains:
                violations.append(
                    f"RET_DOMAIN: Retention strategy '{ret.name}' references unknown domain '{ret.domain}'."
                )
            if not ret.save_signal or not ret.restore_signal:
                violations.append(
                    f"RET_CONTROL: Retention strategy '{ret.name}' missing save/restore control signals."
                )

        return UPFCheckResult(
            rule_family="retention",
            passed=len(violations) == 0,
            violations=violations,
            checked_rules=checked_rules
        )

    def check_supply_network(self) -> UPFCheckResult:
        violations = []
        checked_rules = ["SUPPLY_CLASH"]
        supply_nets = {net.name for net in self.intent.supply_nets}
        for iso in self.intent.isolation_strategies:
            if iso.isolation_signal and iso.isolation_signal in supply_nets:
                violations.append(
                    f"SUPPLY_CLASH: Isolation signal '{iso.isolation_signal}' in strategy '{iso.name}' collides with supply net name."
                )
        return UPFCheckResult(
            rule_family="supply",
            passed=len(violations) == 0,
            violations=violations,
            checked_rules=checked_rules,
        )

    def run_all_checks(self) -> dict[str, UPFCheckResult]:
        """Runs all structural UPF checks."""
        return {
            "isolation": self.check_isolation_clamps(),
            "retention": self.check_retention_registers(),
            "supply": self.check_supply_network(),
        }
