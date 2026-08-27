import argparse
import logging
import sys
from .agents.orchestrator import AgenticOrchestrator

def main():
    parser = argparse.ArgumentParser(description="OpenLEC: Agentic AI LEC & UPF Verification")
    parser.add_argument("rtl_file", help="Path to the Golden RTL file")
    parser.add_argument("--upf", required=True, help="Path to the IEEE 1801 UPF file")
    parser.add_argument("--top", required=True, help="Top module name")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    
    orchestrator = AgenticOrchestrator(
        rtl_file=args.rtl_file,
        upf_file=args.upf,
        top_module=args.top
    )
    
    success = orchestrator.run_verification_flow()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
