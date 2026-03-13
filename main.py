from __future__ import annotations

from pathlib import Path

import click

from dwg_table_exporter.config import ExportConfig
from dwg_table_exporter.pipeline import run_pipeline


@click.command()
@click.option(
    "--dxf-dir",
    "dxf_dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    required=True,
    help="DXF 文件所在目录（一个 DWG 需先转换为一个 DXF）。",
)
@click.option(
    "--output-dir",
    "output_dir",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    required=True,
    help="Excel 输出目录。",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="若目标 Excel 已存在，则覆盖。",
)
@click.option(
    "--recursive",
    is_flag=True,
    default=False,
    help="递归搜索子目录中的 DXF 文件。",
)
def cli(dxf_dir: Path, output_dir: Path, overwrite: bool, recursive: bool) -> None:
    """批量将 DXF 中的表格导出为 Excel."""
    config = ExportConfig(dxf_dir=dxf_dir, output_dir=output_dir, overwrite=overwrite, recursive=recursive)
    run_pipeline(config)


if __name__ == "__main__":
    cli()

