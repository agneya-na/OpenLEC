from ..models import UPFIntent, Verdict
import logging

logger = logging.getLogger(__name__)

class UPFChecker:
    """Performs structural checks on parsed UPF intent."""
    
    def check_isolation_clamps(self, intent: UPFIntent) -> Verdict:
        """Ensures all outputs of switchable domains have isolation rules."""
        # In a full implementation, we would cross-reference domain boundaries 
        # with isolation rules. Here we do a basic sanity check.
        switchable_domains = [d for d in intent.domains if d.name != "PD_TOP"]
        isolated_domains = set(rule.domain for rule in intent.isolation_rules)
        
        missing_isolation = [d.name for d in switchable_domains if d.name not in isolated_domains]
        
        if missing_isolation:
            logger.warning(f"Missing isolation for domains: {missing_isolation}")
            return Verdict.FAIL
            
        return Verdict.PASS