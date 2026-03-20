from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExportConfig:
    dxf_dir: Path
    output_dir: Path
    overwrite: bool = False
    recursive: bool = False
    autosize: bool = True
    min_col_width: float = 8.0
    max_col_width: float = 60.0
    base_row_height: float = 15.0
    dry_run: bool = False

    def ensure_dirs(self) -> None:
        self.dxf_dir = self.dxf_dir.resolve()
        self.output_dir = self.output_dir.resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

