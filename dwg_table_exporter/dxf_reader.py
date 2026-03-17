from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple, Optional

from .acad_table_reader import read_acad_tables_from_layout
from .drawn_table_reader import read_drawn_tables_from_layout
from .io_loader import find_cad_files, load_doc
from .models import TableData
from .reporting import FileReport


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


def read_tables_with_report(path: Path) -> Tuple[List[TableData], FileReport]:
    """读取表格并返回识别统计报告（用于调试与更清晰的日志）。"""
    doc = load_doc(path)
    tables: List[TableData] = []
    report = FileReport(file_name=path.name)

    for layout in doc.layouts:
        stats = report.layout(layout.name)
        tables.extend(
            read_acad_tables_from_layout(layout, layout_name=layout.name, start_index=len(tables) + 1, stats=stats)
        )
        tables.extend(
            read_drawn_tables_from_layout(
                layout,
                layout_name=layout.name,
                start_index=len(tables) + 1,
                stats=stats,
                file_path=str(path),
            )
        )

    return tables, report

