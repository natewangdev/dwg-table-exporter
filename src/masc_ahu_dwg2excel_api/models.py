from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class TableData:
    """一个通用的表格数据结构：名称 + 二维单元格文本 + 合并信息."""

    name: str
    rows: List[List[str]]
    merges: List[Tuple[int, int, int, int]] = field(default_factory=list)  # 0-based, inclusive

