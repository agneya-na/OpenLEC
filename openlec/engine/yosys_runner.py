import subprocess
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

class YosysRunner:
    """Interface to execute Yosys TCL scripts for SAT-based synthesis and LEC."""
    
    def __init__(self, yosys_bin: str = "yosys"):
        self.yosys_bin = yosys_bin

    def run_script(self, script_content: str) -> str:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ys', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            logger.debug(f"Running Yosys script:\n{script_content}")
            result = subprocess.run(
                [self.yosys_bin, '-s', script_path],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                logger.error(f"Yosys failed:\n{result.stderr}")
            return result.stdout + result.stderr
        finally:
            os.unlink(script_path)