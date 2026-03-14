from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
import re

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
            raw_content = read_acad_table_content(acad_table)
            # raw_content 是 list[list[str]]，其中字符串可能包含 MTEXT 格式代码

            cleaned_rows = [[_clean_cell_text(cell) for cell in row] for row in raw_content]

            index = len(tables) + 1
            title, data_rows = _split_title_and_data(cleaned_rows, layout.name, index)
            tables.append(TableData(name=title, rows=data_rows))

    return tables


_MTEXT_FONT_PATTERN = re.compile(r"{\\f[^;]*;")
_MTEXT_CTRL_PATTERN = re.compile(r"\\[A-Za-z]+(?:[0-9.-]+)?")


def _clean_cell_text(value: str) -> str:
    """去掉 MTEXT 格式控制，只保留可读文本."""
    if not value:
        return ""

    text = str(value)

    # 处理换行符
    text = text.replace("\\P", "\n").replace("\\n", "\n")

    # 去掉字体格式前缀，如 {\fSimSun|b0|i0|c134|p2;
    text = _MTEXT_FONT_PATTERN.sub("", text)

    # 去掉控制序列，如 \L \l \H1.0; 等
    text = _MTEXT_CTRL_PATTERN.sub("", text)

    # 去掉多余的大括号
    text = text.replace("{", "").replace("}", "")

    return text.strip()


def _split_title_and_data(rows: List[List[str]], layout_name: str, index: int) -> tuple[str, List[List[str]]]:
    """从表格内容中拆分“标题行”和“数据行”.

    约定：
    - 如果第一行有非空单元格，则认为是表格标题，该行不写入 Excel，只用于 sheet 名。
    - 否则使用布局名+序号作为 sheet 名，整表写入 Excel。
    """
    if not rows:
        return f"{layout_name}_Table{index}", []

    first_row = rows[0]
    non_empty = [cell.strip() for cell in first_row if cell and cell.strip()]

    if non_empty:
        title = non_empty[0]
        data_rows = rows[1:]
    else:
        title = f"{layout_name}_Table{index}"
        data_rows = rows

    return title, data_rows

