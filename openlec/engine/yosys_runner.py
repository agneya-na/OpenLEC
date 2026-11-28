"""Thin subprocess wrapper around the Yosys binary."""
from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class YosysError(RuntimeError):
    """Yosys could not be run, failed, or timed out. ``log`` holds its output."""

    def __init__(self, message: str, log: str = "") -> None:
        super().__init__(message)
        self.log = log


def quote_path(path: str | Path) -> str:
    """Render a file path as a quoted Yosys script argument (spaces, Windows)."""
    text = Path(path).as_posix()
    if '"' in text:
        raise ValueError(f"Unsupported character '\"' in path: {text}")
    return f'"{text}"'


def _as_text(data: str | bytes | None) -> str:
    if data is None:
        return ""
    return data.decode(errors="replace") if isinstance(data, bytes) else data


class YosysRunner:
    """
    Interface to execute Yosys scripts for SAT-based synthesis and LEC.
    Acts as the underlying execution fabric for the Python EDA flow.
    """

    def __init__(self, yosys_bin: str = "yosys", timeout_seconds: float | None = None) -> None:
        self.yosys_bin = yosys_bin
        self.timeout_seconds = timeout_seconds

    def run_script(self, script_content: str) -> str:
        """Write the script to a temp file, run it, and return Yosys stdout."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ys", delete=False) as f:
            f.write(script_content)
            script_path = f.name

        try:
            logger.debug("Executing Yosys script: %s", script_path)
            result = subprocess.run(
                [self.yosys_bin, "-s", script_path],
                check=False,  # the return code is handled below, keeping stdout
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError:
            raise YosysError(f"Yosys binary '{self.yosys_bin}' not found in PATH.") from None
        except subprocess.TimeoutExpired as exc:
            raise YosysError(
                f"Yosys timed out after {self.timeout_seconds}s.",
                log=_as_text(exc.stdout) + _as_text(exc.stderr),
            ) from None
        finally:
            Path(script_path).unlink(missing_ok=True)

        if result.returncode != 0:
            # Yosys reports errors on stdout (its log), not only on stderr.
            log = result.stdout + result.stderr
            errors = [ln.strip() for ln in log.splitlines() if "ERROR:" in ln]
            detail = "; ".join(errors) or result.stderr.strip() or f"exit code {result.returncode}"
            logger.error("Yosys execution failed: %s", detail)
            raise YosysError(f"Yosys execution failed: {detail}", log=log)
        return result.stdout
