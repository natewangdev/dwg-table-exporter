from __future__ import annotations

import os
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
        _apply_odafc_env_override()
        if not odafc.is_installed():
            raise RuntimeError(
                "检测到 DWG 文件，但 ODA File Converter 未配置或不可用。"
                "请在 ezdxf.ini 的 [odafc-addon] 中配置 unix_exec_path/win_exec_path，"
                "或设置环境变量 ODAFC_EXEC_PATH。"
            )
        return odafc.readfile(path)
    raise ValueError(f"不支持的文件类型: {suffix}")


def _apply_odafc_env_override() -> None:
    """允许通过环境变量覆盖 ODA 可执行路径."""
    exec_path = os.getenv("ODAFC_EXEC_PATH", "").strip()
    if not exec_path:
        return
    if os.name == "nt":
        odafc.win_exec_path = exec_path
    else:
        odafc.unix_exec_path = exec_path

