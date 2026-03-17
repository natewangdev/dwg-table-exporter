from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from .acad_table_reader import read_acad_tables_from_layout
from .drawn_table_reader import read_drawn_tables_from_layout
from .io_loader import find_cad_files, load_doc
from .models import TableData


def find_dxf_files(dxf_dir: Path, recursive: bool = False) -> Iterable[Path]:
    """兼容旧函数名：查找目录下的 CAD 文件（.dxf/.dwg）。"""
    return find_cad_files(dxf_dir, recursive=recursive)


def read_tables_from_dxf(path: Path) -> List[TableData]:
    """从单个 CAD 文件中读取表格数据（标准 TABLE + 线段拼表格），支持 DXF 与 DWG."""
    doc = load_doc(path)
    tables: List[TableData] = []

    for layout in doc.layouts:
        tables.extend(read_acad_tables_from_layout(layout, layout_name=layout.name, start_index=len(tables) + 1))
        tables.extend(read_drawn_tables_from_layout(layout, layout_name=layout.name, start_index=len(tables) + 1))

    return tables

