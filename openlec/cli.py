import click
import logging
from rich.console import Console
from .agents import Orchestrator
from .agents.power_intent_agent import PowerIntentAgent
from .agents.equivalence_agent import EquivalenceAgent

console = Console()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

@click.command()
@click.argument('golden_rtl', type=click.Path(exists=True))
@click.argument('revised_rtl', type=click.Path(exists=True))
@click.option('--upf', type=click.Path(exists=True), help='IEEE 1801 UPF file')
@click.option('--top', required=True, help='Top module name')
def main(golden_rtl: str, revised_rtl: str, upf: str, top: str):
    """OpenLEC: Agentic AI LEC & UPF Verification"""
    console.print("[bold green]🚀 OpenLEC Verification Orchestrator[/bold green]")
    
    context = {
        "golden_rtl": golden_rtl,
        "revised_rtl": revised_rtl,
        "upf_file": upf,
        "top_module": top
    }
    
    agents = []
    if upf:
        agents.append(PowerIntentAgent())
    agents.append(EquivalenceAgent())
    
    orchestrator = Orchestrator(agents)
    final_context = orchestrator.run(context)
    
    if final_context.get("halt") and final_context.get("verdict") != "PASS":
        console.print(f"[bold red]❌ VERDICT: FAIL[/bold red] - {final_context.get('reason')}")
    else:
        console.print("[bold green]✅ VERDICT: PASS[/bold green] - Equivalence and UPF checks successful.")

if __name__ == "__main__":
    main()