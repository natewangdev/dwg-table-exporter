from __future__ import annotations

from typing import List


def has_any_content(rows: List[List[str]]) -> bool:
    """Return True if the table contains any non-empty cell (used to filter empty tables)."""
    for row in rows:
        for cell in row:
            if cell and str(cell).strip():
                return True
    return False
