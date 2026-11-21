"""Shared pytest setup."""
from __future__ import annotations

import os
import shutil

import pytest


def pytest_configure(config: pytest.Config) -> None:
    # CI sets OPENLEC_REQUIRE_YOSYS so a broken Yosys install fails the run
    # instead of silently skipping every integration test.
    if os.environ.get("OPENLEC_REQUIRE_YOSYS") and shutil.which("yosys") is None:
        raise pytest.UsageError(
            "OPENLEC_REQUIRE_YOSYS is set but 'yosys' is not on PATH; "
            "the Yosys integration tests would be skipped."
        )
