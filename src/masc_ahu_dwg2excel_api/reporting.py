from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class LayoutStats:
    layout_name: str
    acad_table_found: int = 0
    acad_table_exported: int = 0
    drawn_table_candidates: int = 0
    drawn_table_exported: int = 0
    skipped: Dict[str, int] = field(default_factory=dict)

    def skip(self, reason: str, count: int = 1) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + count


@dataclass
class FileReport:
    file_name: str
    layouts: Dict[str, LayoutStats] = field(default_factory=dict)

    def layout(self, name: str) -> LayoutStats:
        if name not in self.layouts:
            self.layouts[name] = LayoutStats(layout_name=name)
        return self.layouts[name]

    @property
    def acad_table_exported(self) -> int:
        return sum(s.acad_table_exported for s in self.layouts.values())

    @property
    def drawn_table_exported(self) -> int:
        return sum(s.drawn_table_exported for s in self.layouts.values())

    @property
    def total_exported(self) -> int:
        return self.acad_table_exported + self.drawn_table_exported

    @property
    def skipped(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for s in self.layouts.values():
            for k, v in s.skipped.items():
                out[k] = out.get(k, 0) + v
        return out


@dataclass
class ParseContextError(Exception):
    message: str
    file_path: Optional[str] = None
    layout_name: Optional[str] = None
    bbox: Optional[tuple[float, float, float, float]] = None
    grid_size: Optional[tuple[int, int]] = None  # (rows, cols)

    def __str__(self) -> str:  # noqa: D105
        parts = [self.message]
        if self.file_path:
            parts.append(f"file={self.file_path}")
        if self.layout_name:
            parts.append(f"layout={self.layout_name}")
        if self.bbox:
            parts.append(f"bbox={self.bbox}")
        if self.grid_size:
            parts.append(f"grid={self.grid_size[0]}x{self.grid_size[1]}")
        return " | ".join(parts)

