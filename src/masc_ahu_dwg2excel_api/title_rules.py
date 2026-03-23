from __future__ import annotations

from typing import List, Tuple


def looks_like_header_row(row: List[str]) -> bool:
    """Return True if the row looks like a header/field-name row.

    Heuristic: at least 2 non-empty cells (avoids mistaking a drawing title for a table title).
    """
    non_empty = [c.strip() for c in row if c and c.strip()]
    return len(non_empty) >= 2


def split_title_and_data(rows: List[List[str]], layout_name: str, index: int) -> Tuple[str, List[List[str]], int]:
    """Split the first row as a title when it contains only one non-empty cell
    and the next row looks like a header.

    Returns (title, data_rows, title_row_offset) where title_row_offset=1
    means the first row was stripped as a title.
    """
    if not rows:
        return f"{layout_name}_Table{index}", [], 0

    first_row = rows[0]
    non_empty = [cell.strip() for cell in first_row if cell and cell.strip()]

    # Conservative: only treat the first row as a title when it has exactly
    # one non-empty cell AND the following row looks like a header.
    if len(non_empty) == 1 and looks_like_header_row(rows[1] if len(rows) > 1 else []):
        return non_empty[0], rows[1:], 1

    return f"{layout_name}_Table{index}", rows, 0
