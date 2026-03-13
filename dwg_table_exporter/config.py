from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExportConfig:
    dxf_dir: Path
    output_dir: Path
    overwrite: bool = False
    recursive: bool = False

    def ensure_dirs(self) -> None:
        self.dxf_dir = self.dxf_dir.resolve()
        self.output_dir = self.output_dir.resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

