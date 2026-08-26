from dataclasses import dataclass


@dataclass
class LECResult:
    ok: bool
    details: str = ""
