import subprocess
import logging
from pathlib import Path
from ..models.lec_result import LECResult, LECVerdict

logger = logging.getLogger(__name__)

class LECEngine:
    """
    SAT-based Logic Equivalence Checking using Yosys.
    Replaces Conformal's `COMPARE` and `ANALYZE SETUP` commands.
    """
    def __init__(self, yosys_exec: str = "yosys"):
        self.yosys_exec = yosys_exec

    def run_equivalence_check(self, golden_rtl: str, revised_rtl: str, top_module: str) -> LECResult:
        """
        Executes Yosys equiv_* flow to prove equivalence.
        """
        yosys_script = f"""
        # 1. Read Designs (Conformal: READ DESIGN -Golden / -Revised)
        read_verilog {golden_rtl}
        rename {top_module} golden
        read_verilog {revised_rtl}
        rename {top_module} revised

        # 2. Hierarchy & Flatten (Conformal: FLATTEN / SET FLATTEN MODEL)
        hierarchy -top golden
        proc; opt; memory; opt

        # 3. Create Equivalence Miter (Conformal: MAP KEY POINTS)
        equiv_make golden revised equiv

        # 4. SAT Solving (Conformal: COMPARE)
        equiv_simple equiv
        equiv_sat -prove equiv
        
        # 5. Extract Status (Conformal: REPORT COMPARE DATA)
        equiv_status equiv
        """
        
        script_path = Path("yosys_lec_script.ys")
        script_path.write_text(yosys_script)
        
        try:
            result = subprocess.run(
                [self.yosys_exec, "-s", str(script_path)],
                capture_output=True, text=True, timeout=300
            )
            return self._parse_yosys_output(result.stdout)
        except subprocess.TimeoutExpired:
            # Maps to Conformal's ABORT status
            return LECResult(verdict=LECVerdict.ABORT, message="SAT solver timed out (Abort). Run ANALYZE ABORT.")
        except Exception as e:
            return LECResult(verdict=LECVerdict.ABORT, message=f"Execution failed: {str(e)}")

    def _parse_yosys_output(self, stdout: str) -> LECResult:
        if "Equivalence successfully proven" in stdout or "Proved" in stdout:
            return LECResult(verdict=LECVerdict.EQUIVALENT, message="Designs are functionally equivalent.")
        elif "UNPROVEN" in stdout or "Not equivalent" in stdout:
            return LECResult(verdict=LECVerdict.NONEQUIVALENT, message="Found nonequivalent points.")
        else:
            return LECResult(verdict=LECVerdict.ABORT, message="SAT solver aborted or inconclusive.")
