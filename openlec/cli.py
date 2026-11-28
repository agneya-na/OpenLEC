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
from openlec.engine.design_source import (
    DesignSource,
    DesignSourceError,
    FileList,
    parse_define,
    parse_filelist,
)
from openlec.engine.yosys_runner import YosysRunner

EPILOG = """\
file lists:
  -f/--revised-f lists resolve relative paths from the current directory;
  -F/--revised-F lists resolve them from the list's own folder. Lists may use
  +incdir+DIR, +define+NAME=VAL, -I, -D, -v FILE and nested -f/-F.
  Files ending in .sv/.svh are read as SystemVerilog; --sv applies it to all.
"""


class _UsageError(Exception):
    """Bad command-line input: printed as `openlec: error: ...`, exit code 2."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openlec",
        description="OpenLEC: Agentic AI LEC + UPF power-aware equivalence verification",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "rtl_files", nargs="*", metavar="rtl_file", help="Golden RTL/netlist file(s)"
    )
    golden = parser.add_argument_group("golden design inputs")
    golden.add_argument("-f", dest="filelists", action="append", default=[], metavar="LIST",
                        help="Golden file list (paths relative to the current directory)")
    golden.add_argument("-F", dest="filelists_rel", action="append", default=[],
                        metavar="LIST",
                        help="Golden file list (paths relative to the list's folder)")
    revised = parser.add_argument_group("revised design inputs")
    revised.add_argument(
        "--revised", action="append", default=[], metavar="FILE",
        help="Revised netlist file to check against the golden design, e.g. a synthesized "
        "netlist; repeat for several files (default: the golden design itself)",
    )
    revised.add_argument("--revised-f", dest="revised_filelists", action="append", default=[],
                         metavar="LIST",
                         help="Revised file list (paths relative to the current directory)")
    revised.add_argument("--revised-F", dest="revised_filelists_rel", action="append",
                         default=[], metavar="LIST",
                         help="Revised file list (paths relative to the list's folder)")
    shared = parser.add_argument_group("options for both designs")
    shared.add_argument("-I", "--include-dir", dest="include_dirs", action="append",
                        default=[], metavar="DIR", help="Add an `include search directory")
    shared.add_argument("-D", "--define", dest="defines", action="append", default=[],
                        metavar="NAME[=VALUE]", help="Define a Verilog macro")
    shared.add_argument("--sv", action="store_true",
                        help="Read every file as SystemVerilog (.sv/.svh always are)")

    parser.add_argument("--upf", default=None, help="IEEE 1801 UPF file")
    parser.add_argument("--top", required=True, help="Top module name")
    parser.add_argument("--iterations", type=int, default=3, help="Optimization iterations")
    parser.add_argument("--delay-budget", type=float, default=10.0, help="Delay budget (ns)")
    parser.add_argument("--power-budget", type=float, default=1000.0, help="Power budget (uW)")
    parser.add_argument("--config", type=Path, default=None, help="YAML config file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    return parser


def _build_source(
    label: str,
    files: list[str],
    filelists: list[str],
    filelists_rel: list[str],
    args: argparse.Namespace,
) -> DesignSource | None:
    """Merge direct files and file lists for one side, plus the shared -I/-D/--sv."""
    for f in files:
        if not Path(f).exists():
            raise _UsageError(f"{label} file not found: {f}")
    merged = FileList(files=[Path(f) for f in files])
    lists = [(f, False) for f in filelists] + [(f, True) for f in filelists_rel]
    for spec, relative_to_list in lists:
        fl = parse_filelist(spec, relative_to_list=relative_to_list)
        merged.files += fl.files
        merged.include_dirs += fl.include_dirs
        merged.defines.update(fl.defines)
        for opt in fl.ignored:
            print(f"openlec: warning: {spec}: ignoring unsupported option '{opt}'",
                  file=sys.stderr)
    if not merged.files:
        return None
    defines = dict(merged.defines)
    for item in args.defines:  # command-line -D overrides file-list defines
        name, value = parse_define(item)
        defines[name] = value
    source = DesignSource.from_paths(
        merged.files, [*args.include_dirs, *merged.include_dirs], defines, sv=args.sv
    )
    for kind, path in source.missing():
        raise _UsageError(f"{label} {kind} not found: {path}")
    source.read_script()  # validate include dirs and defines up front
    return source


def _is_plain(source: DesignSource) -> bool:
    return len(source.files) == 1 and not (source.include_dirs or source.defines or source.sv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    file_cfg = load_config_file(args.config)
    revised_files = list(args.revised)
    no_revised_args = not (revised_files or args.revised_filelists or args.revised_filelists_rel)
    if no_revised_args and file_cfg.get("revised_file"):
        revised_files = [file_cfg["revised_file"]]
    try:
        golden = _build_source("RTL", args.rtl_files, args.filelists, args.filelists_rel, args)
        if golden is None:
            raise _UsageError("no golden design files given (pass rtl_file(s), -f or -F)")
        revised = _build_source(
            "revised", revised_files, args.revised_filelists, args.revised_filelists_rel, args
        )
        if args.upf and not Path(args.upf).exists():
            raise _UsageError(f"UPF file not found: {args.upf}")
    except (_UsageError, DesignSourceError) as exc:
        print(f"openlec: error: {exc}", file=sys.stderr)
        return 2

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    config = OpenLECConfig(
        rtl_file=str(golden.files[0]),
        revised_file=str(revised.files[0]) if revised else None,
        top_module=args.top,
        upf_file=args.upf or file_cfg.get("upf_file"),
        iterations=args.iterations,
        delay_budget_ns=args.delay_budget,
        power_budget_uw=args.power_budget,
        verbose=args.verbose,
        yosys_exec=file_cfg.get("yosys_path", "yosys"),
        timeout_seconds=file_cfg.get("timeout_seconds"),
    )
    ctx = config.to_context()
    if not _is_plain(golden):
        ctx.golden_source = golden
    if revised is not None and not _is_plain(revised):
        ctx.revised_source = revised
    runner = YosysRunner(config.yosys_exec, timeout_seconds=config.timeout_seconds)
    report = AgenticOrchestrator(ctx, runner).run_verification_flow()
    print(ReportingAgent.render(report))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
