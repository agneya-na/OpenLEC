"""End-to-end demo: agentic verification over the bundled example designs.

Requires Yosys on PATH for a PASS verdict; without Yosys the LEC gate
reports ABORT and the flow fails gracefully.
"""
from __future__ import annotations

import sys
from pathlib import Path

from openlec.agents.orchestrator import AgenticOrchestrator
from openlec.models.schemas import VerificationContext

EXAMPLES = [
    ("counter", "designs/counter.v", "upf/counter.upf"),
    ("mac_unit", "designs/mac_unit.v", "upf/mac_unit.upf"),
]


def main() -> int:
    base = Path(__file__).resolve().parent
    exit_code = 0

    for top, rtl, upf in EXAMPLES:
        ctx = VerificationContext(
            rtl_file=base / rtl,
            top_module=top,
            upf_file=base / upf,
            iterations=2,
            delay_budget_ns=10.0,
            power_budget_uw=1000.0,
        )
        report = AgenticOrchestrator(ctx).run_verification_flow()
        print(report.to_text())
        if not report.passed:
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
