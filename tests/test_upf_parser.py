"""Yosys-free tests for the UPF parser and structural checker."""
from __future__ import annotations

from openlec.engine.upf_checker import UPFChecker
from openlec.engine.upf_parser import UPFParser

UPF_TEXT = """\
# top-level always-on domain
set_design_top chip_top
create_power_domain PD_TOP -include_scope
create_power_domain PD_CORE -elements {u_core u_mem}

create_supply_net VDD -domain PD_TOP
create_supply_net VSS

set_isolation iso_core \\
    -domain PD_CORE \\
    -clamp_value 0 \\
    -applies_to outputs \\
    -isolation_signal iso_en \\
    -isolation_sense high

set_retention ret_core -domain PD_CORE -retention_power_net VDD \\
    -save_signal save_en -restore_signal restore_en
"""

SHUFFLED_ISOLATION = """\
create_power_domain PD_CORE -elements {u_core}
set_isolation iso_x -clamp_value 1 -domain PD_CORE -applies_to inputs
"""


class TestUPFParser:
    def test_parse_full_intent(self, tmp_path):
        upf = tmp_path / "design.upf"
        upf.write_text(UPF_TEXT)

        intent = UPFParser(upf).parse()

        assert intent.design_top == "chip_top"
        assert intent.domain_names() == ["PD_TOP", "PD_CORE"]
        assert intent.power_domains[0].include_scope is True
        assert intent.power_domains[1].elements == ["u_core", "u_mem"]
        assert {n.name for n in intent.supply_nets} == {"VDD", "VSS"}
        assert intent.supply_nets[0].domain == "PD_TOP"

    def test_isolation_options_are_order_independent(self, tmp_path):
        upf = tmp_path / "shuffled.upf"
        upf.write_text(SHUFFLED_ISOLATION)

        intent = UPFParser(upf).parse()
        iso = intent.isolation_strategies[0]

        assert iso.name == "iso_x"
        assert iso.domain == "PD_CORE"
        assert iso.clamp_value == "1"
        assert iso.applies_to == "inputs"

    def test_retention_and_helpers(self, tmp_path):
        upf = tmp_path / "design.upf"
        upf.write_text(UPF_TEXT)

        intent = UPFParser(upf).parse()
        ret = intent.retention_strategies[0]

        assert ret.name == "ret_core"
        assert ret.save_signal == "save_en"
        assert ret.restore_signal == "restore_en"
        assert ret.retention_power_net == "VDD"
        assert intent.isolated_domains() == {"PD_CORE"}
        assert intent.retained_domains() == {"PD_CORE"}

    def test_parse_file_alias(self, tmp_path):
        upf = tmp_path / "design.upf"
        upf.write_text(UPF_TEXT)

        intent = UPFParser(tmp_path / "unused.upf").parse_file(upf)

        assert intent.design_top == "chip_top"


class TestUPFChecker:
    def _intent(self, tmp_path, text=UPF_TEXT):
        upf = tmp_path / "design.upf"
        upf.write_text(text)
        return UPFParser(upf).parse()

    def test_all_checks_pass_on_good_intent(self, tmp_path):
        checks = UPFChecker(self._intent(tmp_path)).run_all_checks()

        assert set(checks) == {"isolation", "retention", "supply"}
        assert all(result.passed for result in checks.values())

    def test_missing_isolation_is_flagged(self, tmp_path):
        intent = self._intent(tmp_path, """\
            create_power_domain PD_TOP -include_scope
            create_power_domain PD_CORE -elements {u_core}
            """)

        result = UPFChecker(intent).check_isolation_clamps()

        assert result.passed is False
        assert any("ISO_MISSING" in v for v in result.violations)

    def test_retention_without_control_signals_is_flagged(self, tmp_path):
        intent = self._intent(tmp_path, """\
            create_power_domain PD_CORE -elements {u_core}
            set_isolation iso -domain PD_CORE -clamp_value 0
            set_retention ret_bad -domain PD_CORE -save_signal save_en
            """)

        result = UPFChecker(intent).check_retention_registers()

        assert result.passed is False
        assert any("RET_CONTROL" in v for v in result.violations)

    def test_retention_unknown_domain_is_flagged(self, tmp_path):
        intent = self._intent(tmp_path, """\
            create_power_domain PD_CORE -elements {u_core}
            set_retention ret_x -domain PD_MISSING \\
                -save_signal s -restore_signal r
            """)

        result = UPFChecker(intent).check_retention_registers()

        assert any("RET_DOMAIN" in v for v in result.violations)

    def test_isolation_signal_colliding_with_supply_is_flagged(self, tmp_path):
        intent = self._intent(tmp_path, """\
            create_power_domain PD_CORE -elements {u_core}
            create_supply_net VDD
            set_isolation iso -domain PD_CORE -clamp_value 0 \\
                -isolation_signal VDD
            """)

        result = UPFChecker(intent).check_supply_network()

        assert result.passed is False
        assert any("SUPPLY_CLASH" in v for v in result.violations)