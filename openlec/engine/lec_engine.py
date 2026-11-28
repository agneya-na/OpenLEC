"""SAT-based Logic Equivalence Checking on top of Yosys.

The check runs in two phases (Conformal analogue in brackets):

1. Prove   [READ DESIGN / ANALYZE SETUP / COMPARE]
   Each design is read into its own Yosys design (``design -stash``), so
   designs that share submodule names never collide, then flattened. The
   ``equiv_make`` / ``equiv_simple`` / ``equiv_induct`` / ``equiv_status``
   flow tries to prove every compare point.
2. Refute  [ANALYZE ABORT]
   Only when compare points stay unproven: a miter of the two designs is
   bounded-model-checked from an all-zero initial state. A model is a real
   counterexample (NONEQUIVALENT). No model within the bound means the
   result is inconclusive (ABORT).

The verdict comes from the counts that ``equiv_status`` prints and from the
SAT result line, not from searching the log for keywords.
"""
from __future__ import annotations

import logging
import re

from openlec.engine.design_source import NetlistLike, as_source
from openlec.engine.yosys_runner import YosysError, YosysRunner
from openlec.models.lec_result import LECResult, LECVerdict

logger = logging.getLogger(__name__)

DEFAULT_BMC_DEPTH = 10

_FOUND_RE = re.compile(r"Found (\d+) \$equiv cells in")
_STATUS_RE = re.compile(r"Of those cells (\d+) are proven and (\d+) are unproven")
_CEX_FOUND = "SAT proof finished - model found: FAIL!"
_CEX_TABLE_RE = re.compile(r"^[ \t]*Time[ \t]+Signal Name", re.MULTILINE)


class LECEngine:
    """
    SAT-based Logic Equivalence Checking using Yosys.
    Maps to Conformal's `READ DESIGN`, `ANALYZE SETUP`, `COMPARE`, and `ANALYZE ABORT`.
    """

    def __init__(self, runner: YosysRunner | None = None, bmc_depth: int = DEFAULT_BMC_DEPTH):
        self.runner = runner or YosysRunner()
        self.bmc_depth = bmc_depth

    # ------------------------------------------------------------------ scripts
    @staticmethod
    def _load_pair_script(golden: NetlistLike, revised: NetlistLike, top: str) -> str:
        """READ DESIGN + ANALYZE SETUP: load each side in isolation as `gold` / `gate`."""

        def prepare(design: NetlistLike, stash: str) -> str:
            return (
                as_source(design).read_script()
                + f"hierarchy -check -top {top}\n"
                "proc\n"
                "flatten\n"
                "memory\n"
                "async2sync\n"
                "opt_clean\n"
                f"design -stash {stash}\n"
            )

        return (
            prepare(golden, "gold")
            + prepare(revised, "gate")
            + f"design -copy-from gold -as gold {top}\n"
            + f"design -copy-from gate -as gate {top}\n"
        )

    def _prove_script(self, golden: NetlistLike, revised: NetlistLike, top: str) -> str:
        return self._load_pair_script(golden, revised, top) + (
            "equiv_make gold gate equiv\n"
            "hierarchy -top equiv\n"
            "equiv_simple\n"
            "equiv_induct\n"
            "equiv_status\n"
        )

    def _refute_script(self, golden: NetlistLike, revised: NetlistLike, top: str) -> str:
        return self._load_pair_script(golden, revised, top) + (
            "miter -equiv -flatten -make_assert -ignore_gold_x gold gate miter\n"
            "hierarchy -top miter\n"
            f"sat -prove-asserts -set-init-zero -seq {self.bmc_depth} "
            "-show-inputs -show-outputs miter\n"
        )

    # ------------------------------------------------------------------ flow
    def run_equivalence_check(
        self, golden_rtl: NetlistLike, revised_rtl: NetlistLike, top_module: str
    ) -> LECResult:
        """Executes the complete LEC flow and returns a verdict."""
        try:
            prove_log = self.runner.run_script(
                self._prove_script(golden_rtl, revised_rtl, top_module)
            )
        except (RuntimeError, ValueError) as exc:  # Yosys failure or bad design source
            return self._failure("LEC setup failed", exc)

        total, unproven = self._parse_status(prove_log)
        if total is None or unproven is None:
            return LECResult(
                verdict=LECVerdict.ABORT,
                message="Could not read the equiv_status summary from the Yosys log.",
                yosys_log=prove_log,
            )
        if total == 0:
            return LECResult(
                verdict=LECVerdict.INCONCLUSIVE,
                message="No compare points: no matching outputs/registers to compare.",
                yosys_log=prove_log,
            )
        if unproven == 0:
            return LECResult(
                verdict=LECVerdict.EQUIVALENT,
                message=f"Designs are equivalent: all {total} compare points proven by SAT.",
                compare_points=total,
                yosys_log=prove_log,
            )

        # Some points are unproven: look for a concrete counterexample.
        try:
            bmc_log = self.runner.run_script(
                self._refute_script(golden_rtl, revised_rtl, top_module)
            )
        except RuntimeError as exc:
            result = self._failure(
                f"{unproven} of {total} compare points unproven; counterexample search failed",
                exc,
            )
            return result.model_copy(update={"compare_points": total, "abort_points": unproven})

        log = prove_log + bmc_log
        if _CEX_FOUND in bmc_log:
            return LECResult(
                verdict=LECVerdict.NONEQUIVALENT,
                message=(
                    f"Designs are NOT equivalent: counterexample found within "
                    f"{self.bmc_depth} cycles from an all-zero initial state "
                    f"({unproven} of {total} compare points unproven)."
                ),
                compare_points=total,
                nonequivalent_points=unproven,
                counterexample=self._extract_counterexample(bmc_log),
                yosys_log=log,
            )
        return LECResult(
            verdict=LECVerdict.ABORT,
            message=(
                f"Inconclusive: {unproven} of {total} compare points unproven and no "
                f"counterexample within {self.bmc_depth} cycles."
            ),
            compare_points=total,
            abort_points=unproven,
            yosys_log=log,
        )

    # ------------------------------------------------------------------ parsing
    @staticmethod
    def _parse_status(log: str) -> tuple[int | None, int | None]:
        """Return (total, unproven) from the last `equiv_status` summary."""
        found = _FOUND_RE.findall(log)
        if not found:
            return None, None
        total = int(found[-1])
        if total == 0:
            return 0, 0
        status = _STATUS_RE.findall(log)
        if not status:
            return total, None
        return total, int(status[-1][1])

    @staticmethod
    def _extract_counterexample(log: str) -> str:
        """Return the signal/value table that `sat -show-*` prints for a model."""
        match = _CEX_TABLE_RE.search(log)
        if not match:
            return ""
        lines: list[str] = []
        for line in log[match.start():].splitlines():
            # The table is indented and ends at the first blank/unindented line.
            if not line.strip() or not line.startswith(" ") or len(lines) >= 200:
                break
            lines.append(line.rstrip())
        return "\n".join(lines)

    @staticmethod
    def _failure(prefix: str, exc: Exception) -> LECResult:
        logger.error("%s: %s", prefix, exc)
        return LECResult(
            verdict=LECVerdict.ABORT,
            message=f"{prefix}: {exc}",
            abort_points=1,
            yosys_log=exc.log if isinstance(exc, YosysError) else "",
        )
