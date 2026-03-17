from __future__ import annotations

from pathlib import Path
from typing import Iterable

import ezdxf
from ezdxf.addons import odafc


def find_cad_files(root_dir: Path, recursive: bool = False) -> Iterable[Path]:
    """查找目录下的 CAD 文件，支持 .dxf 与 .dwg."""
    for path in root_dir.rglob("*") if recursive else root_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {".dxf", ".dwg"}:
            yield path


def load_doc(path: Path):
    """根据扩展名选择合适的加载方式.

    - .dxf: 直接使用 ezdxf.readfile
    - .dwg: 使用 ezdxf.addons.odafc.readfile（需要安装 ODA File Converter）
    """
    suffix = path.suffix.lower()
    if suffix == ".dxf":
        return ezdxf.readfile(path)
    if suffix == ".dwg":
        return odafc.readfile(path)
    raise ValueError(f"不支持的文件类型: {suffix}")

