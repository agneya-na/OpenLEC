import subprocess
import sys
import os

def run_demo():
    print("🔧 Running OpenLEC Demo...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    golden = os.path.join(base_dir, "designs", "counter.v")
    revised = os.path.join(base_dir, "designs", "counter.v") # Using same for PASS demo
    upf = os.path.join(base_dir, "upf", "counter.upf")
    
    cmd = [
        sys.executable, "-m", "openlec.cli",
        golden, revised,
        "--upf", upf,
        "--top", "counter"
    ]
    
    subprocess.run(cmd)

if __name__ == "__main__":
    run_demo()