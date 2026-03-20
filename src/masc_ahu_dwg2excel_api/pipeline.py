from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .config import ExportConfig
from .dxf_reader import TableData, find_dxf_files, read_tables_with_report
from .excel_writer import save_workbook_for_dxf, tables_to_workbook
from .reporting import ParseContextError


def process_single_dxf(config: ExportConfig, dxf_path: Path) -> Path | None:
    tables, report = read_tables_with_report(dxf_path)

    if not tables:
        _print_report(report)
        return None

    _print_report(report)

    if config.dry_run:
        return None

    wb = tables_to_workbook(
        tables,
        autosize=config.autosize,
        min_col_width=config.min_col_width,
        max_col_width=config.max_col_width,
        base_row_height=config.base_row_height,
    )
    return save_workbook_for_dxf(config.output_dir, dxf_path, wb, overwrite=config.overwrite)


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
        except ParseContextError as exc:
            print(f"  [失败] {exc}")
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"  [失败] file={dxf_path} -> {exc}")
            continue

        if excel_path is None:
            if config.dry_run:
                print("  [完成] dry-run：未写出 Excel")
            else:
                print("  [跳过] 未找到可导出的表格数据")
        else:
            print(f"  [完成] 导出为 {excel_path.name}")


def _print_report(report) -> None:
    acad = report.acad_table_exported
    drawn = report.drawn_table_exported
    total = report.total_exported
    skipped = report.skipped
    skipped_str = ", ".join(f"{k}={v}" for k, v in sorted(skipped.items())) if skipped else "none"
    print(f"  [统计] tables: total={total} acad_table={acad} drawn={drawn}; skipped: {skipped_str}")

