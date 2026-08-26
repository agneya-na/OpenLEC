from .yosys_runner import YosysRunner
from ..models import LECResult
import re
import logging

logger = logging.getLogger(__name__)

class LECEngine:
    """SAT-based Logic Equivalence Checking using Yosys `equiv_*` flow."""
    
    def __init__(self, runner: YosysRunner):
        self.runner = runner

    def check_equivalence(self, golden_file: str, revised_file: str, top_module: str) -> LECResult:
        script = f"""
        # Read Golden Design
        read_verilog {golden_file}
        rename {top_module} golden
        
        # Read Revised Design
        read_verilog {revised_file}
        rename {top_module} revised
        
        # Prepare equivalence checking
        equiv_make golden revised equiv
        equiv_simple equiv
        equiv_induct equiv
        
        # Check status
        equiv_status -assert equiv
        """
        
        output = self.runner.run_script(script)
        
        # Parse Yosys output for equivalence status
        is_eq = "Equivalence successfully proven" in output
        unproven = len(re.findall(r"Unproven", output))
        
        return LECResult(
            equivalent=is_eq,
            yosys_log=output,
            nonequivalent_points=unproven
        )