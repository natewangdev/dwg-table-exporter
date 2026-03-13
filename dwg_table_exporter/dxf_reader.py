from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import ezdxf
from ezdxf.addons import odafc
from ezdxf.entities.acad_table import read_acad_table_content


@dataclass
class TableData:
    """一个通用的表格数据结构：名称 + 二维单元格文本."""

    name: str
    rows: List[List[str]]


def find_dxf_files(dxf_dir: Path, recursive: bool = False) -> Iterable[Path]:
    """查找目录下的 CAD 文件，支持 .dxf 与 .dwg."""
    pattern = "**/*" if recursive else "*"
    for path in dxf_dir.glob(pattern):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".dxf", ".dwg"}:
            return_paths = []  # type: ignore[assignment]
            # 为了保持生成器语义，这里使用局部列表收集，再 yield
            # 但是 ApplyPatch 语法限制，不便重写为生成器表达式，改为简单实现：
            # 实际上，这里可以直接 yield；为简洁起见重写整个函数更好
    # 上面的实现不合适，改为直接使用 rglob：


def find_dxf_files(dxf_dir: Path, recursive: bool = False) -> Iterable[Path]:
    pattern = "**/*" if recursive else "*"
    for path in dxf_dir.rglob("*") if recursive else dxf_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {".dxf", ".dwg"}:
            yield path


def _load_doc(path: Path) -> ezdxf.EzDxfDoc:  # type: ignore[name-defined]
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


def read_tables_from_dxf(path: Path) -> List[TableData]:
    """从单个 CAD 文件中读取所有 ACAD_TABLE 表格数据，支持 DXF 与 DWG."""
    doc = _load_doc(path)

    tables: List[TableData] = []

    # 遍历所有布局（模型空间 + 纸空间）
    for layout in doc.layouts:
        # 在该布局中查找 ACAD_TABLE 实体
        for acad_table in layout.query("ACAD_TABLE"):
            content = read_acad_table_content(acad_table)
            # content 是 list[list[str]]，已全部转换为字符串

            # 表名：优先用布局名 + 编号
            index = len(tables) + 1
            table_name = f"{layout.name}_Table{index}"
            tables.append(TableData(name=table_name, rows=content))

    return tables

