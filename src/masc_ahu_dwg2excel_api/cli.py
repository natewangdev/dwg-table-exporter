"""CLI: batch-export tables from DWG/DXF files to Excel."""

from __future__ import annotations

from pathlib import Path

import click

from masc_ahu_dwg2excel_api.config import ExportConfig
from masc_ahu_dwg2excel_api.pipeline import run_pipeline


@click.command()
@click.option(
    "--dxf-dir",
    "dxf_dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    required=True,
    help="Directory containing DWG/DXF files.",
)
@click.option(
    "--output-dir",
    "output_dir",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    required=True,
    help="Output directory for Excel files.",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite existing Excel files.",
)
@click.option(
    "--recursive",
    is_flag=True,
    default=False,
    help="Recursively search subdirectories for CAD files.",
)
@click.option(
    "--autosize/--no-autosize",
    default=True,
    show_default=True,
    help="Auto-adjust column width / row height based on content.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    show_default=True,
    help="Only detect and report tables without writing Excel files.",
)
def main(
    dxf_dir: Path,
    output_dir: Path,
    overwrite: bool,
    recursive: bool,
    autosize: bool,
    dry_run: bool,
) -> None:
    """Batch-export tables from DWG/DXF files to Excel."""
    config = ExportConfig(
        dxf_dir=dxf_dir,
        output_dir=output_dir,
        overwrite=overwrite,
        recursive=recursive,
        autosize=autosize,
        dry_run=dry_run,
    )
    run_pipeline(config)


if __name__ == "__main__":
    main()
