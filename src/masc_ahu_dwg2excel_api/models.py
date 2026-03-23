from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class TableData:
    """Generic table data: name + 2-D cell text + merge info."""

    name: str
    rows: List[List[str]]
    merges: List[Tuple[int, int, int, int]] = field(default_factory=list)  # 0-based, inclusive
