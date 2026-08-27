"""LEC integration tests (skipped automatically when Yosys is absent)."""
from __future__ import annotations

import shutil

import pytest

from openlec.engine.lec_engine import LECEngine
from openlec.models.lec_result import LECVerdict

pytestmark = pytest.mark.skipif(
    shutil.which("yosys") is None,
    reason="Yosys not installed; skipping LEC integration tests.",
)


def test_lec_equivalence_identical(tmp_path):
    rtl = tmp_path / "top.v"
    rtl.write_text("module top(input a, output b); assign b = a; endmodule\n")

    result = LECEngine().run_equivalence_check(str(rtl), str(rtl), "top")

    assert result.verdict is LECVerdict.EQUIVALENT
    assert result.nonequivalent_points == 0


def test_lec_nonequivalent(tmp_path):
    golden = tmp_path / "g.v"
    revised = tmp_path / "r.v"
    golden.write_text("module top(input a, output b); assign b = a; endmodule\n")
    revised.write_text("module top(input a, output b); assign b = ~a; endmodule\n")

    result = LECEngine().run_equivalence_check(str(golden), str(revised), "top")

    assert result.verdict is not LECVerdict.EQUIVALENT
