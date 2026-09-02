"""OpenLEC CLI entrypoint (argparse, stdlib-only)."""
from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from openlec.agents.orchestrator import AgenticOrchestrator
from openlec.agents.reporting_agent import ReportingAgent
from openlec.config import OpenLECConfig, load_config_file
from openlec.engine.yosys_runner import YosysRunner


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openlec",
        description="OpenLEC: Agentic AI LEC + UPF power-aware equivalence verification",
    )
    parser.add_argument("rtl_file", help="Golden RTL/netlist file")
    parser.add_argument("--upf", default=None, help="IEEE 1801 UPF file")
    parser.add_argument("--top", required=True, help="Top module name")
    parser.add_argument("--iterations", type=int, default=3, help="Optimization iterations")
    parser.add_argument("--delay-budget", type=float, default=10.0, help="Delay budget (ns)")
    parser.add_argument("--power-budget", type=float, default=1000.0, help="Power budget (uW)")
    parser.add_argument("--config", type=Path, default=None, help="YAML config file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    rtl_path = Path(args.rtl_file)
    if not rtl_path.exists():
        return 2
    if args.upf and not Path(args.upf).exists():
        return 2
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    file_cfg = load_config_file(args.config)
    config = OpenLECConfig(
        rtl_file=args.rtl_file,
        top_module=args.top,
        upf_file=args.upf or file_cfg.get("upf_file"),
        iterations=args.iterations,
        delay_budget_ns=args.delay_budget,
        power_budget_uw=args.power_budget,
        verbose=args.verbose,
        yosys_exec=file_cfg.get("yosys_path", "yosys"),
    )
    runner = YosysRunner(config.yosys_exec)
    report = AgenticOrchestrator(config.to_context(), runner).run_verification_flow()
    print(ReportingAgent.render(report))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
