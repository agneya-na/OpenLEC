"""Parses RTL/UPF inputs and seeds the context (Conformal: READ DESIGN / READ POWER INTENT)."""
from __future__ import annotations

from pathlib import Path

from openlec.agents import BaseAgent
from openlec.engine.design_source import DesignSource, as_source
from openlec.engine.upf_parser import UPFParser
from openlec.models.schemas import VerificationContext


def _check_source(source: DesignSource, file_label: str) -> str | None:
    """Return a halt reason if the design source is unusable, else None."""
    missing = source.missing()
    if missing:
        kind, path = missing[0]
        label = file_label if kind == "file" else "Include directory"
        return f"{label} not found: {path}"
    try:
        source.read_script()  # validates include dirs and defines
    except ValueError as exc:
        return f"Design input error: {exc}"
    return None


class ParsingAgent(BaseAgent):
    name = "parsing"

    def execute(self, ctx: VerificationContext) -> VerificationContext:
        # Single files stay plain paths; multi-file inputs are DesignSources.
        golden: DesignSource | Path = ctx.golden_source or Path(ctx.rtl_file)
        if ctx.revised_source is not None:
            revised: DesignSource | Path = ctx.revised_source
        elif ctx.revised_file:
            revised = Path(ctx.revised_file)
        else:
            revised = golden  # without --revised: golden checked against itself

        for source, label in ((golden, "RTL file"), (revised, "Revised netlist")):
            reason = _check_source(as_source(source), label)
            if reason:
                ctx.halt(reason)
                return ctx

        if ctx.upf_file:
            upf = Path(ctx.upf_file)
            if not upf.exists():
                ctx.halt(f"UPF file not found: {upf}")
                return ctx
            try:
                ctx.upf_intent = UPFParser(upf).parse()
            except (OSError, ValueError) as exc:  # unreadable file or invalid UPF value
                ctx.halt(f"UPF parse error in {upf}: {exc}")
                return ctx
            if not ctx.top_module and ctx.upf_intent.design_top:
                ctx.top_module = ctx.upf_intent.design_top
        ctx.golden_netlist = golden
        ctx.revised_netlist = revised
        self.log(
            ctx,
            f"Parsed golden={golden}, revised={revised}"
            + (f", UPF domains={ctx.upf_intent.domain_names()}" if ctx.upf_intent else ""),
        )
        return ctx
