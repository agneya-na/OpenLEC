"""Parses RTL/UPF inputs and seeds the context (Conformal: READ POWER INTENT)."""
from __future__ import annotations

from pathlib import Path

from openlec.agents import BaseAgent
from openlec.engine.upf_parser import UPFParser
from openlec.models.schemas import VerificationContext


class ParsingAgent(BaseAgent):
    name = "parsing"

    def execute(self, ctx: VerificationContext) -> VerificationContext:
        rtl = Path(ctx.rtl_file)
        if not rtl.exists():
            ctx.halt(f"RTL file not found: {rtl}")
            return ctx
        if ctx.upf_file:
            upf = Path(ctx.upf_file)
            if not upf.exists():
                ctx.halt(f"UPF file not found: {upf}")
                return ctx
            ctx.upf_intent = UPFParser(upf).parse()
            if not ctx.top_module and ctx.upf_intent.design_top:
                ctx.top_module = ctx.upf_intent.design_top
        ctx.golden_netlist = rtl
        ctx.revised_netlist = rtl  # baseline: revised == golden
        self.log(ctx, f"Parsed RTL={rtl.name}" + (f", UPF domains={ctx.upf_intent.domain_names()}" if ctx.upf_intent else ""))
        return ctx