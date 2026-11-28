"""Multi-file / SystemVerilog design inputs and .f file lists.

Unit tests need no Yosys; integration tests skip when Yosys is absent.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from openlec.agents.optimization_agent import OptimizationAgent
from openlec.engine.design_source import (
    DesignSource,
    DesignSourceError,
    as_source,
    parse_define,
    parse_filelist,
)
from openlec.engine.lec_engine import LECEngine
from openlec.engine.timing_estimator import TimingEstimator
from openlec.models.lec_result import LECVerdict
from openlec.models.optimization_step import StepVerdict
from openlec.models.schemas import VerificationContext

requires_yosys = pytest.mark.skipif(
    shutil.which("yosys") is None,
    reason="Yosys not installed; skipping design-input integration tests.",
)

SV_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "designs" / "sv"


def _touch(path: Path, text: str = "module m; endmodule\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# ---------------------------------------------------------------- DesignSource
class TestDesignSource:
    def test_reads_each_file_with_shared_options(self, tmp_path):
        a = _touch(tmp_path / "a.v")
        b = _touch(tmp_path / "rtl dir" / "b.sv")
        inc = tmp_path / "inc"
        src = DesignSource.from_paths([a, b], [inc], {"WIDTH": "8", "FAST": None})

        lines = src.read_script().splitlines()

        assert lines[0] == "design -reset-vlog"  # no macros leak in from earlier reads
        opts = f"-I{inc.as_posix()} -DWIDTH=8 -DFAST"
        assert lines[1] == f'read_verilog {opts} "{a.as_posix()}"'
        assert lines[2] == f'read_verilog -sv {opts} "{b.as_posix()}"'  # .sv suffix

    def test_sv_flag_applies_to_every_file(self, tmp_path):
        src = DesignSource.from_paths([tmp_path / "a.v", tmp_path / "b.v"], sv=True)

        reads = src.read_script().splitlines()[1:]

        assert all(line.startswith("read_verilog -sv ") for line in reads)

    def test_single_path_is_wrapped(self, tmp_path):
        src = as_source(tmp_path / "top.v")

        assert src.files == (tmp_path / "top.v",)
        assert str(src) == str(tmp_path / "top.v")
        assert as_source(src) is src

    def test_include_dir_with_space_falls_back_to_relative_path(self, tmp_path, monkeypatch):
        project = tmp_path / "my project"
        (project / "inc").mkdir(parents=True)
        monkeypatch.chdir(project)

        script = DesignSource.from_paths([project / "a.v"], [project / "inc"]).read_script()

        assert " -Iinc " in script

    def test_include_dir_with_unavoidable_space_is_an_error(self, tmp_path, monkeypatch):
        (tmp_path / "inc dir").mkdir()
        monkeypatch.chdir(tmp_path)
        src = DesignSource.from_paths([tmp_path / "a.v"], [tmp_path / "inc dir"])

        with pytest.raises(DesignSourceError, match="contains a space"):
            src.read_script()

    @pytest.mark.parametrize("text", ["1BAD", "W=", "W=a b", 'W="x"', ""])
    def test_invalid_defines_are_rejected(self, text):
        with pytest.raises(DesignSourceError):
            parse_define(text)

    def test_valid_defines(self):
        assert parse_define("WIDTH=8") == ("WIDTH", "8")
        assert parse_define("FAST") == ("FAST", None)

    def test_missing_lists_files_and_include_dirs(self, tmp_path):
        a = _touch(tmp_path / "a.v")
        src = DesignSource.from_paths([a, tmp_path / "gone.v"], [tmp_path / "no_inc"])

        assert src.missing() == [
            ("file", tmp_path / "gone.v"),
            ("include directory", tmp_path / "no_inc"),
        ]

    def test_cache_key_changes_when_a_file_changes(self, tmp_path):
        a = _touch(tmp_path / "a.v")
        src = DesignSource.from_paths([a])
        before = src.cache_key()
        st = a.stat()
        os.utime(a, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))

        assert src.cache_key() != before

    def test_str_shortens_long_file_lists(self, tmp_path):
        src = DesignSource.from_paths([tmp_path / f"f{i}.v" for i in range(5)])

        assert str(src).endswith("(+2 more)")


# ---------------------------------------------------------------- file lists
class TestFileList:
    def test_files_incdirs_defines_and_comments(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENLEC_TEST_ROOT", str(tmp_path))
        lst = _touch(tmp_path / "lists" / "top.f", """\
// a comment
# another comment
+incdir+inc+inc2
+define+WIDTH=8+FAST
-I other -Dmode=2 -D DEBUG
rtl/a.v   // trailing comment
"rtl/with space.v"
-v lib/cells.v
${OPENLEC_TEST_ROOT}/abs.v
""")
        base = lst.parent

        fl = parse_filelist(lst, relative_to_list=True)

        assert fl.files == [
            base / "rtl/a.v", base / "rtl/with space.v", base / "lib/cells.v", tmp_path / "abs.v"
        ]
        assert fl.include_dirs == [base / "inc", base / "inc2", base / "other"]
        assert fl.defines == {"WIDTH": "8", "FAST": None, "mode": "2", "DEBUG": None}
        assert fl.ignored == []

    def test_dash_f_resolves_from_cwd_and_dash_capital_f_from_list(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        lst = _touch(tmp_path / "sub" / "x.f", "a.v\n")

        from_cwd = parse_filelist(lst).files
        from_list = parse_filelist(lst, relative_to_list=True).files

        assert [p.resolve() for p in from_cwd] == [(tmp_path / "a.v").resolve()]
        assert from_list == [tmp_path / "sub" / "a.v"]

    def test_nested_lists(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _touch(tmp_path / "sub" / "inner.f", "b.v\n")
        _touch(tmp_path / "cwd.f", "c.v\n")
        top = _touch(tmp_path / "top.f", "a.v\n-F sub/inner.f\n-f cwd.f\n")

        files = [p.resolve() for p in parse_filelist(top, relative_to_list=True).files]

        assert files == [
            (tmp_path / "a.v").resolve(),
            (tmp_path / "sub" / "b.v").resolve(),  # -F: relative to inner.f
            (tmp_path / "c.v").resolve(),  # -f: relative to the current directory
        ]

    def test_cycle_is_an_error(self, tmp_path):
        _touch(tmp_path / "a.f", "-F b.f\n")
        _touch(tmp_path / "b.f", "-F a.f\n")

        with pytest.raises(DesignSourceError, match="includes itself"):
            parse_filelist(tmp_path / "a.f", relative_to_list=True)

    def test_missing_nested_list_is_an_error(self, tmp_path):
        top = _touch(tmp_path / "top.f", "-F nope.f\n")

        with pytest.raises(DesignSourceError, match="Cannot read file list"):
            parse_filelist(top, relative_to_list=True)

    def test_unsupported_options_are_reported_not_read_as_files(self, tmp_path):
        top = _touch(tmp_path / "top.f", "-y libdir +libext+.v -timescale 1ns/1ps a.v\n")

        fl = parse_filelist(top, relative_to_list=True)

        assert fl.files == [tmp_path / "a.v"]
        assert fl.ignored == ["-y libdir", "+libext+.v", "-timescale 1ns/1ps"]

    def test_option_without_argument_is_an_error(self, tmp_path):
        top = _touch(tmp_path / "top.f", "a.v\n-v\n")

        with pytest.raises(DesignSourceError, match="needs an argument"):
            parse_filelist(top, relative_to_list=True)


def test_lec_script_resets_macros_before_each_design(tmp_path):
    class _Runner:
        script = ""

        def run_script(self, script):
            _Runner.script = script
            return "Found 1 $equiv cells in equiv:\n  Of those cells 1 are proven and 0 are unproven.\n"

    golden = DesignSource.from_paths([tmp_path / "g1.v", tmp_path / "g2.sv"], defines={"A": "1"})
    revised = DesignSource.from_paths([tmp_path / "r.v"])

    result = LECEngine(_Runner()).run_equivalence_check(golden, revised, "top")
    lines = _Runner.script.splitlines()

    assert result.verdict is LECVerdict.EQUIVALENT
    resets = [i for i, line in enumerate(lines) if line == "design -reset-vlog"]
    stash_gold = lines.index("design -stash gold")
    assert len(resets) == 2 and resets[0] < stash_gold < resets[1]
    assert any(line.startswith("read_verilog -sv -DA=1 ") for line in lines)


def test_bad_design_option_aborts_lec_instead_of_crashing(tmp_path, monkeypatch):
    (tmp_path / "inc dir").mkdir()
    monkeypatch.chdir(tmp_path)
    src = DesignSource.from_paths([tmp_path / "a.v"], [tmp_path / "inc dir"])

    class _NeverRun:
        def run_script(self, script):
            raise AssertionError("Yosys must not run with an invalid design source")

    result = LECEngine(_NeverRun()).run_equivalence_check(src, src, "top")

    assert result.verdict is LECVerdict.ABORT
    assert "contains a space" in result.message


# ---------------------------------------------------------------- integration
COUNTER = """\
module counter(input clk, input rst, output reg [3:0] out);
    always @(posedge clk or posedge rst)
        if (rst) out <= 4'd0;
        else     out <= out + `STEP;
endmodule
"""


def _sv_example(tmp_path: Path) -> DesignSource:
    copy = tmp_path / "sv"
    shutil.copytree(SV_EXAMPLE, copy)
    fl = parse_filelist(copy / "accum_top.f", relative_to_list=True)
    return DesignSource.from_paths(fl.files, fl.include_dirs, fl.defines)


@requires_yosys
def test_sv_example_from_filelist_is_equivalent_to_itself(tmp_path):
    src = _sv_example(tmp_path)

    result = LECEngine().run_equivalence_check(src, src, "accum_top")

    assert result.verdict is LECVerdict.EQUIVALENT, result.message


@requires_yosys
def test_defines_change_the_design(tmp_path):
    rtl = _touch(tmp_path / "counter.v", COUNTER)
    golden = DesignSource.from_paths([rtl], defines={"STEP": "1"})
    revised = DesignSource.from_paths([rtl], defines={"STEP": "2"})

    result = LECEngine().run_equivalence_check(golden, revised, "counter")

    assert result.verdict is LECVerdict.NONEQUIVALENT


@requires_yosys
def test_macros_do_not_leak_from_golden_into_revised(tmp_path):
    defs = _touch(tmp_path / "defs.v", "`define STEP 1\n")
    rtl = _touch(tmp_path / "counter.v", COUNTER)
    golden = DesignSource.from_paths([defs, rtl])
    revised = DesignSource.from_paths([rtl])  # never defines STEP

    result = LECEngine().run_equivalence_check(golden, revised, "counter")

    assert result.verdict is LECVerdict.ABORT
    assert "undefined macro" in result.message


@requires_yosys
def test_stats_and_optimizer_accept_design_sources(tmp_path):
    src = _sv_example(tmp_path)
    ctx = VerificationContext(rtl_file=src.files[0], top_module="accum_top", iterations=2)
    ctx.golden_netlist = ctx.revised_netlist = src

    assert TimingEstimator().stats(src, "accum_top").cells > 0
    ctx = OptimizationAgent().execute(ctx)

    assert [s.verdict for s in ctx.steps] == [StepVerdict.ACCEPT, StepVerdict.ACCEPT], [
        s.reject_reason for s in ctx.steps
    ]
