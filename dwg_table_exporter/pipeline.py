from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .config import ExportConfig
from .dxf_reader import TableData, find_dxf_files, read_tables_from_dxf
from .excel_writer import save_workbook_for_dxf, tables_to_workbook


def process_single_dxf(config: ExportConfig, dxf_path: Path) -> Path | None:
    tables: Iterable[TableData] = read_tables_from_dxf(dxf_path)
    tables = list(tables)

    if not tables:
        # 暂时允许没有表格时跳过，也可以选择仍然导出一个空 Excel
        return None

    wb = tables_to_workbook(tables)
    excel_path = save_workbook_for_dxf(config.output_dir, dxf_path, wb, overwrite=config.overwrite)
    return excel_path


def run_pipeline(config: ExportConfig) -> None:
    config.ensure_dirs()
    dxf_files = list(find_dxf_files(config.dxf_dir, recursive=config.recursive))

    if not dxf_files:
        print(f"在目录 {config.dxf_dir} 下没有找到 DXF 文件")
        return

    print(f"找到 {len(dxf_files)} 个 DXF 文件，开始处理...")
    for dxf_path in dxf_files:
        print(f"- 处理: {dxf_path.name}")
        try:
            excel_path = process_single_dxf(config, dxf_path)
        except Exception as exc:  # noqa: BLE001
            print(f"  [失败] {dxf_path} -> {exc}")
            continue

        if excel_path is None:
            print("  [跳过] 未找到表格数据")
        else:
            print(f"  [完成] 导出为 {excel_path.name}")

