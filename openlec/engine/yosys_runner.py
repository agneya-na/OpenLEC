import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

class YosysRunner:
    """
    Interface to execute Yosys TCL scripts for SAT-based synthesis and LEC.
    Acts as the underlying execution fabric for the Python EDA flow.
    """
    
    def __init__(self, yosys_bin: str = "yosys"):
        self.yosys_bin = yosys_bin

    def run_script(self, script_content: str) -> str:
        """Writes Yosys script to a temp file and executes it."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ys', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            logger.debug(f"Executing Yosys script: {script_path}")
            result = subprocess.run(
                [self.yosys_bin, "-s", script_path],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Yosys execution failed:\n{e.stderr}")
            raise RuntimeError(f"Yosys execution failed: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError(f"Yosys binary '{self.yosys_bin}' not found in PATH.")
        finally:
            Path(script_path).unlink(missing_ok=True)
