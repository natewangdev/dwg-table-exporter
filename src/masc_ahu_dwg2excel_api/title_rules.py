from __future__ import annotations

from typing import List, Tuple


def looks_like_header_row(row: List[str]) -> bool:
    """判断一行是否更像“表头/字段名行”。

    经验规则：至少 2 个非空单元格（避免把图纸总标题误判为表格标题）。
    """
    non_empty = [c.strip() for c in row if c and c.strip()]
    return len(non_empty) >= 2


def split_title_and_data(rows: List[List[str]], layout_name: str, index: int) -> Tuple[str, List[List[str]], int]:
    """拆分“标题行”和“数据行”。

    返回 (title, data_rows, title_row_offset)，title_row_offset=1 表示剔除首行作为标题。
    """
    if not rows:
        return f"{layout_name}_Table{index}", [], 0

    first_row = rows[0]
    non_empty = [cell.strip() for cell in first_row if cell and cell.strip()]

    # 更保守：只有“首行仅 1 个非空单元格”且下一行更像表头时才认为是标题行
    if len(non_empty) == 1 and looks_like_header_row(rows[1] if len(rows) > 1 else []):
        return non_empty[0], rows[1:], 1

    return f"{layout_name}_Table{index}", rows, 0

