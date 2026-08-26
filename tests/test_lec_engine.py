import pytest
import os
from openlec.engine.yosys_runner import YosysRunner
from openlec.engine.lec_engine import LECEngine

def test_yosys_runner():
    runner = YosysRunner()
    # Simple Yosys script to check if it's installed and running
    out = runner.run_script("echo 'Hello OpenLEC'")
    assert "Hello OpenLEC" in out

def test_lec_equivalence():
    runner = YosysRunner()
    engine = LECEngine(runner)
    
    # Create dummy identical files for testing
    with open("test_golden.v", "w") as f:
        f.write("module top(input a, output b); assign b = a; endmodule")
    with open("test_revised.v", "w") as f:
        f.write("module top(input a, output b); assign b = a; endmodule")
        
    result = engine.check_equivalence("test_golden.v", "test_revised.v", "top")
    assert result.equivalent is True
    
    os.remove("test_golden.v")
    os.remove("test_revised.v")