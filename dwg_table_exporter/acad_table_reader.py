from __future__ import annotations

from typing import List, Optional

from ezdxf.entities.acad_table import read_acad_table_content

from .models import TableData
from .reporting import LayoutStats
from .table_filters import has_any_content
from .text_clean import clean_cell_text
from .title_rules import split_title_and_data


def read_acad_tables_from_layout(
    layout, *, layout_name: str, start_index: int, stats: Optional[LayoutStats] = None
) -> List[TableData]:
    tables: List[TableData] = []
    next_index = start_index

    for acad_table in layout.query("ACAD_TABLE"):
        if stats:
            stats.acad_table_found += 1
        raw_content = read_acad_table_content(acad_table)
        cleaned_rows = [[clean_cell_text(cell) for cell in row] for row in raw_content]

        title, data_rows, _title_offset = split_title_and_data(cleaned_rows, layout_name, next_index)
        if not has_any_content(data_rows):
            if stats:
                stats.skip("empty_table")
        else:
            tables.append(TableData(name=title, rows=data_rows))
            if stats:
                stats.acad_table_exported += 1

        next_index += 1

    return tables

