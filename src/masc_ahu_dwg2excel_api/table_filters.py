from __future__ import annotations

from typing import List


def has_any_content(rows: List[List[str]]) -> bool:
    """判断表格是否有任何非空内容（用于过滤空表）."""
    for row in rows:
        for cell in row:
            if cell and str(cell).strip():
                return True
    return False

