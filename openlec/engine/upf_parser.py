"""IEEE 1801 UPF parser (open-source counterpart of READ POWER INTENT).

Order-independent option parsing: UPF options may appear in any order and
may span lines via backslash continuation.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

from openlec.models.upf_models import (
    IsolationStrategy, PowerDomain, RetentionStrategy, SupplyNet, UPFIntent,
)

logger = __import__("logging").getLogger(__name__)

_COMMANDS = (
    "set_design_top", "create_power_domain", "create_supply_net",
    "set_isolation", "set_retention",
)
_COMMAND_RE = re.compile(r"^\s*(" + "|".join(_COMMANDS) + r")\b", re.MULTILINE)


def _option(chunk: str, name: str) -> str | None:
    m = re.search(rf"-{name}\s+(\{{[^}}]*\}}|\S+)", chunk)
    if not m:
        return None
    value = m.group(1)
    return value[1:-1] if value.startswith("{") and value.endswith("}") else value


def _flag(chunk: str, name: str) -> bool:
    return re.search(rf"-{name}\b", chunk) is not None


class UPFParser:
    def __init__(self, upf_file: str | Path) -> None:
        self.upf_file = Path(upf_file)

    def parse(self) -> UPFIntent:
        return self.parse_text(self.upf_file.read_text())

    def parse_file(self, upf_file: str | Path) -> UPFIntent:
        """Backward-compatible alias."""
        self.upf_file = Path(upf_file)
        return self.parse()

    def parse_text(self, content: str) -> UPFIntent:
        cleaned = re.sub(r"#[^\n]*", "", content)
        cleaned = re.sub(r"\\\s*\n", " ", cleaned)
        intent = UPFIntent(raw_content=content)
        for kind, chunk in self._split_commands(cleaned):
            getattr(self, f"_parse_{kind}")(chunk, intent)
        logger.info(
            "Parsed UPF: %d domain(s), %d isolation, %d retention",
            len(intent.power_domains), len(intent.isolation_strategies),
            len(intent.retention_strategies),
        )
        return intent

    @staticmethod
    def _split_commands(content: str) -> List[Tuple[str, str]]:
        matches = list(_COMMAND_RE.finditer(content))
        return [
            (m.group(1), content[m.start(1):matches[i + 1].start() if i + 1 < len(matches) else len(content)].strip())
            for i, m in enumerate(matches)
        ]

    @staticmethod
    def _parse_set_design_top(chunk: str, intent: UPFIntent) -> None:
        m = re.match(r"set_design_top\s+([^\s-]\S*)", chunk)
        if m:
            intent.design_top = m.group(1).strip("/")

    @staticmethod
    def _parse_create_power_domain(chunk: str, intent: UPFIntent) -> None:
        m = re.match(r"create_power_domain\s+([A-Za-z_][\w]*)", chunk)
        if not m:
            return
        elements = (_option(chunk, "elements") or "").split()
        intent.power_domains.append(PowerDomain(
            name=m.group(1), elements=elements, include_scope=_flag(chunk, "include_scope"),
        ))

    @staticmethod
    def _parse_create_supply_net(chunk: str, intent: UPFIntent) -> None:
        m = re.match(r"create_supply_net\s+([A-Za-z_][\w]*)", chunk)
        if m:
            intent.supply_nets.append(SupplyNet(name=m.group(1), domain=_option(chunk, "domain")))

    @staticmethod
    def _parse_set_isolation(chunk: str, intent: UPFIntent) -> None:
        m = re.match(r"set_isolation\s+([A-Za-z_][\w]*)", chunk)
        if not m or not _option(chunk, "domain"):
            return
        intent.isolation_strategies.append(IsolationStrategy(
            name=m.group(1),
            domain=_option(chunk, "domain") or "",
            applies_to=_option(chunk, "applies_to") or "outputs",
            clamp_value=_option(chunk, "clamp_value") or "0",
            isolation_signal=_option(chunk, "isolation_signal"),
            isolation_sense=_option(chunk, "isolation_sense") or "high",
            location=_option(chunk, "location") or "parent",
        ))

    @staticmethod
    def _parse_set_retention(chunk: str, intent: UPFIntent) -> None:
        m = re.match(r"set_retention\s+([A-Za-z_][\w]*)", chunk)
        if not m or not _option(chunk, "domain"):
            return
        intent.retention_strategies.append(RetentionStrategy(
            name=m.group(1),
            domain=_option(chunk, "domain") or "",
            retention_power_net=_option(chunk, "retention_power_net"),
            retention_ground_net=_option(chunk, "retention_ground_net"),
            save_signal=_option(chunk, "save_signal"),
            restore_signal=_option(chunk, "restore_signal"),
        ))
