import logging

from ..models.lec_result import LECResult, LECVerdict
from .yosys_runner import YosysRunner

logger = logging.getLogger(__name__)

class LECEngine:
    """
    SAT-based Logic Equivalence Checking using Yosys.
    Maps directly to Conformal's `READ DESIGN`, `ANALYZE SETUP`, `COMPARE`, and `ANALYZE ABORT`.
    """
    
    def __init__(self, runner: YosysRunner | None = None):
        self.runner = runner or YosysRunner()

    def run_equivalence_check(self, golden_rtl: str, revised_rtl: str, top_module: str) -> LECResult:
        """
        Executes the complete LEC flow.
        """
        # Yosys script mapping Conformal's setup and compare phases
        yosys_script = f"""
        # ---------------------------------------------------------
        # 1. READ DESIGN (Conformal: READ DESIGN -golden/-revised)
        # ---------------------------------------------------------
        read_verilog {golden_rtl}
        rename {top_module} golden
        read_verilog {revised_rtl}
        rename {top_module} revised
        
        # ---------------------------------------------------------
        # 2. ANALYZE SETUP (Conformal: ANALYZE SETUP / FLATTEN)
        # Hierarchy resolution, process/memory/FSM extraction
        # ---------------------------------------------------------
        hierarchy -top golden
        hierarchy -top revised
        proc; opt; memory; opt; fsm; opt -full
        
        # ---------------------------------------------------------
        # 3. COMPARE (Conformal: ADD COMPARED POINTS -all / COMPARE)
        # SAT-based miter creation and inductive proving
        # ---------------------------------------------------------
        equiv_make golden revised equiv
        equiv_induct equiv
        
        # ---------------------------------------------------------
        # 4. ANALYZE ABORT (Conformal: ANALYZE ABORT / REPORT COMPARE DATA)
        # Extracting status of mapped, unmapped, and aborted points
        # ---------------------------------------------------------
        equiv_status equiv
        """
        
        try:
            stdout = self.runner.run_script(yosys_script)
            return self._parse_yosys_output(stdout)
        except RuntimeError as e:
            logger.error(f"LEC Flow crashed: {e!s}")
            return LECResult(
                verdict=LECVerdict.ABORT,
                message=f"LEC Flow crashed during execution: {e!s}",
                unmapped_points=0,
                abort_points=1
            )

    def _parse_yosys_output(self, stdout: str) -> LECResult:
        """
        Parses Yosys equiv_status output to map to Conformal's EQ/NEQ/Abort statuses.
        """
        unmapped = 0
        aborts = 0
        proved = False
        
        for line in stdout.splitlines():
            line_lower = line.lower()
            # Mapping Yosys outputs to Conformal's Compare Results table
            if "unmapped" in line_lower or "not mapped" in line_lower:
                unmapped += 1
            if "abort" in line_lower or "sat" in line_lower or "failed" in line_lower:
                aborts += 1
            if "proved" in line_lower or "equivalent" in line_lower:
                proved = True
                
        # Decision Logic based on Conformal's priority rules
        if aborts > 0:
            verdict = LECVerdict.ABORT
            msg = f"SAT solver aborted/inconclusive. Aborts: {aborts}, Unmapped: {unmapped}"
        elif unmapped > 0:
            verdict = LECVerdict.ABORT
            msg = f"Unmapped points detected. Unmapped: {unmapped}"
        elif proved:
            verdict = LECVerdict.EQUIVALENT
            msg = "Designs are functionally equivalent (Proved by SAT)."
        else:
            verdict = LECVerdict.NONEQUIVALENT
            msg = "Designs are NOT equivalent (Counterexample found)."
            
        return LECResult(
            verdict=verdict,
            message=msg,
            unmapped_points=unmapped,
            abort_points=aborts
        )
