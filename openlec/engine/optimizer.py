import logging
from .yosys_runner import YosysRunner
from .lec_engine import LECEngine
from .timing_estimator import TimingEstimator
from .power_estimator import PowerEstimator
from ..models.optimization_step import OptimizationStep, Verdict
from ..models.metrics import DesignMetrics
from ..models.lec_result import LECVerdict

logger = logging.getLogger(__name__)

class OptimizationEngine:
    """
    Applies synthesis optimization passes and enforces LEC/UPF/Metric gates.
    Replaces manual Conformal dofile iterations with an automated AI-driven loop.
    """
    
    def __init__(self, yosys_runner: YosysRunner, lec_engine: LECEngine):
        self.runner = yosys_runner
        self.lec_engine = lec_engine
        self.timing_est = TimingEstimator()
        self.power_est = PowerEstimator()

    def apply_pass_and_verify(
        self, 
        iteration: int,
        pass_name: str, 
        golden_rtl: str, 
        current_revised_rtl: str, 
        top_module: str,
        delay_budget: float,
        power_budget: float
    ) -> OptimizationStep:
        
        # 1. Apply Synthesis Pass (e.g., opt, fsm, share, opt_clean)
        logger.info(f"[Iter {iteration}] Applying Yosys pass: '{pass_name}'")
        out_file = f"optimized_iter{iteration}.v"
        
        script = f"""
        read_verilog {current_revised_rtl}
        hierarchy -top {top_module}
        {pass_name}
        opt_clean -purge
        write_verilog -noattr {out_file}
        """
        
        try:
            self.runner.run_script(script)
        except Exception as e:
            return OptimizationStep(
                iteration=iteration, pass_name=pass_name, verdict=Verdict.REJECT,
                reject_reason=f"Synthesis pass crashed: {e}",
                revised_netlist=current_revised_rtl
            )
            
        # 2. Enforce LEC Gate (Conformal COMPARE equivalent)
        logger.info(f"[Iter {iteration}] Enforcing LEC Equivalence Gate...")
        lec_result = self.lec_engine.run_equivalence_check(golden_rtl, out_file, top_module)
        
        if lec_result.verdict != LECVerdict.EQUIVALENT:
            logger.warning(f"[Iter {iteration}] LEC Gate FAILED: {lec_result.message}")
            return OptimizationStep(
                iteration=iteration, pass_name=pass_name, verdict=Verdict.REJECT,
                reject_reason=f"LEC failed: {lec_result.message}",
                revised_netlist=current_revised_rtl # Revert to previous safe state
            )
            
        # 3. Enforce Metric Budgets (Timing & Power)
        delay = self.timing_est.estimate(out_file)
        power = self.power_est.estimate(out_file)
        metrics = DesignMetrics(delay_ns=delay, power_uw=power, area_cells=0)
        
        if delay > delay_budget:
            return OptimizationStep(
                iteration=iteration, pass_name=pass_name, verdict=Verdict.REJECT,
                reject_reason=f"Timing violation: {delay}ns > {delay_budget}ns",
                revised_netlist=current_revised_rtl, metrics=metrics
            )
            
        if power > power_budget:
            return OptimizationStep(
                iteration=iteration, pass_name=pass_name, verdict=Verdict.REJECT,
                reject_reason=f"Power violation: {power}uW > {power_budget}uW",
                revised_netlist=current_revised_rtl, metrics=metrics
            )
            
        # 4. Accept Pass
        logger.info(f"[Iter {iteration}] Pass '{pass_name}' ACCEPTED. Metrics: Delay={delay}ns, Power={power}uW")
        return OptimizationStep(
            iteration=iteration, pass_name=pass_name, verdict=Verdict.ACCEPT,
            revised_netlist=out_file, metrics=metrics
        )