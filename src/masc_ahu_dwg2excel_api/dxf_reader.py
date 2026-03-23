from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple, Optional

from .acad_table_reader import read_acad_tables_from_layout
from .drawn_table_reader import read_drawn_tables_from_layout
from .io_loader import find_cad_files, load_doc
from .models import TableData
from .reporting import FileReport


def find_dxf_files(dxf_dir: Path, recursive: bool = False) -> Iterable[Path]:
    """Legacy alias: find CAD files (.dxf/.dwg) under the given directory."""
    return find_cad_files(dxf_dir, recursive=recursive)


def read_tables_from_dxf(path: Path) -> List[TableData]:
    """Read table data from a single CAD file (ACAD_TABLE + drawn tables). Supports DXF and DWG."""
    doc = load_doc(path)
    tables: List[TableData] = []

    for layout in doc.layouts:
        tables.extend(read_acad_tables_from_layout(layout, layout_name=layout.name, start_index=len(tables) + 1))
        tables.extend(read_drawn_tables_from_layout(layout, layout_name=layout.name, start_index=len(tables) + 1))

    return tables


def read_tables_with_report(path: Path) -> Tuple[List[TableData], FileReport]:
    """Read tables and return a recognition report for debugging / logging."""
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
