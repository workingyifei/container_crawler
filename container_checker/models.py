from dataclasses import dataclass
from typing import Optional


@dataclass
class ContainerStatus:
    container_number: str
    terminal: Optional[str] = None
    available: Optional[str] = None
    line_operator: Optional[str] = None
    dimensions: Optional[str] = None
    customs_hold: Optional[str] = None
    line_hold: Optional[str] = None
    cbpa_hold: Optional[str] = None
    terminal_hold: Optional[str] = None
    location: Optional[str] = None
