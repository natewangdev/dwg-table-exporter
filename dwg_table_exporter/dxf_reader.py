from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Dict
import re

import ezdxf
from ezdxf.addons import odafc
from ezdxf.entities.acad_table import read_acad_table_content
from ezdxf.math import Vec3


@dataclass
class TableData:
    """一个通用的表格数据结构：名称 + 二维单元格文本."""

    name: str
    rows: List[List[str]]
    merges: List[Tuple[int, int, int, int]] = field(default_factory=list)  # 0-based, inclusive


def find_dxf_files(dxf_dir: Path, recursive: bool = False) -> Iterable[Path]:
    """查找目录下的 CAD 文件，支持 .dxf 与 .dwg."""
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
    """从单个 CAD 文件中读取表格数据（标准 TABLE + 线段拼表格），支持 DXF 与 DWG."""
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
            if _has_any_content(data_rows):
                tables.append(TableData(name=title, rows=data_rows))

        # 如果没有标准 TABLE，也尝试解析“线段+文字”表格
        drawn_tables = _read_drawn_tables_from_layout(layout, layout_name=layout.name, start_index=len(tables) + 1)
        tables.extend([t for t in drawn_tables if _has_any_content(t.rows)])

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

    # 更保守：只有“首行仅 1 个非空单元格”且下一行更像表头时才认为是标题行
    if len(non_empty) == 1 and _looks_like_header_row(rows[1] if len(rows) > 1 else []):
        title = non_empty[0]
        data_rows = rows[1:]
    else:
        title = f"{layout_name}_Table{index}"
        data_rows = rows

    return title, data_rows


def _looks_like_header_row(row: List[str]) -> bool:
    """判断一行是否更像“表头/字段名行”。

    经验规则：至少 2 个非空单元格（避免把图纸总标题误判为表格标题）。
    """
    non_empty = [c.strip() for c in row if c and c.strip()]
    return len(non_empty) >= 2


def _has_any_content(rows: List[List[str]]) -> bool:
    """判断表格是否有任何非空内容（用于过滤空表）."""
    for row in rows:
        for cell in row:
            if cell and str(cell).strip():
                return True
    return False


# -----------------------------
# 线段 + 文字拼表格（网格识别）
# -----------------------------

_GRID_TOL = 1e-3  # 几何容差（单位：图纸单位）
_CLUSTER_PAD = 5.0  # 聚类 padding（单位：图纸单位）


@dataclass(frozen=True)
class _Seg:
    x1: float
    y1: float
    x2: float
    y2: float
    orient: str  # "H" or "V"

    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        return (min(self.x1, self.x2), min(self.y1, self.y2), max(self.x1, self.x2), max(self.y1, self.y2))


def _read_drawn_tables_from_layout(layout, layout_name: str, start_index: int) -> List[TableData]:
    segs = _extract_axis_aligned_segments(layout)
    if not segs:
        return []

    clusters = _cluster_segments(segs, pad=_CLUSTER_PAD)
    tables: List[TableData] = []
    next_index = start_index

    for cluster in clusters:
        xs, ys = _cluster_grid_lines(cluster)
        if xs is None or ys is None:
            continue

        # 过滤：仅 1×1 网格（常见于图框/标题栏矩形）直接跳过
        if (len(xs) - 1) == 1 and (len(ys) - 1) == 1:
            continue

        bbox = _bbox_from_lines(xs, ys)
        grid = _build_grid(cluster, xs, ys)
        rows = _fill_cells_from_text(layout, xs, ys, bbox)
        if not rows:
            continue

        merges, normalized_rows = _apply_merges_for_drawn_table(rows, grid)

        # 过滤：只有 1 个非空单元格的“表格”（容易把图纸总标题误识别成表格）
        non_empty_cells = sum(1 for row in normalized_rows for cell in row if cell and cell.strip())
        if non_empty_cells < 2:
            continue

        title, data_rows, title_row_offset = _split_title_and_data_drawn_with_offset(
            normalized_rows, layout_name=layout_name, index=next_index
        )
        # 如果标题行被剔除，需要同步调整 merge 的行号
        adj_merges = _shift_merges_row(merges, -title_row_offset)

        tables.append(TableData(name=title, rows=data_rows, merges=adj_merges))
        next_index += 1

    return tables


def _extract_axis_aligned_segments(layout) -> List[_Seg]:
    segs: List[_Seg] = []

    def add_seg(p1: Vec3, p2: Vec3) -> None:
        x1, y1 = float(p1.x), float(p1.y)
        x2, y2 = float(p2.x), float(p2.y)
        dx = x2 - x1
        dy = y2 - y1
        if abs(dx) <= _GRID_TOL and abs(dy) > _GRID_TOL:
            segs.append(_Seg(x1=x1, y1=y1, x2=x2, y2=y2, orient="V"))
        elif abs(dy) <= _GRID_TOL and abs(dx) > _GRID_TOL:
            segs.append(_Seg(x1=x1, y1=y1, x2=x2, y2=y2, orient="H"))

    for e in layout.query("LINE"):
        add_seg(e.dxf.start, e.dxf.end)

    for e in layout.query("LWPOLYLINE"):
        pts = [Vec3(x, y, 0.0) for x, y, *_ in e.get_points("xy")]
        if len(pts) < 2:
            continue
        for p1, p2 in zip(pts, pts[1:]):
            add_seg(p1, p2)
        if e.closed:
            add_seg(pts[-1], pts[0])

    for e in layout.query("POLYLINE"):
        pts = [v.dxf.location for v in e.vertices()]
        if len(pts) < 2:
            continue
        for p1, p2 in zip(pts, pts[1:]):
            add_seg(p1, p2)
        if e.is_closed:
            add_seg(pts[-1], pts[0])

    return segs


def _cluster_segments(segs: List[_Seg], pad: float) -> List[List[_Seg]]:
    n = len(segs)
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    def overlap(b1: Tuple[float, float, float, float], b2: Tuple[float, float, float, float]) -> bool:
        x1, y1, x2, y2 = b1
        a1, b1_, a2, b2_ = b2
        return not (x2 < a1 or a2 < x1 or y2 < b1_ or b2_ < y1)

    bboxes = []
    for s in segs:
        x1, y1, x2, y2 = s.bbox
        bboxes.append((x1 - pad, y1 - pad, x2 + pad, y2 + pad))

    # O(n^2) 简单聚类：通常表格线数量不大
    for i in range(n):
        for j in range(i + 1, n):
            if overlap(bboxes[i], bboxes[j]):
                union(i, j)

    groups: Dict[int, List[_Seg]] = {}
    for i, s in enumerate(segs):
        r = find(i)
        groups.setdefault(r, []).append(s)

    return list(groups.values())


def _cluster_grid_lines(cluster: List[_Seg]) -> Tuple[Optional[List[float]], Optional[List[float]]]:
    xs: List[float] = []
    ys: List[float] = []
    for s in cluster:
        if s.orient == "V":
            xs.append(s.x1)
            xs.append(s.x2)
        else:
            ys.append(s.y1)
            ys.append(s.y2)

    xs_u = _unique_sorted(xs, tol=1e-2)
    ys_u = _unique_sorted(ys, tol=1e-2)

    # 至少需要 2 条竖线 + 2 条横线
    if len(xs_u) < 2 or len(ys_u) < 2:
        return None, None

    return xs_u, ys_u


def _unique_sorted(values: List[float], tol: float) -> List[float]:
    if not values:
        return []
    values = sorted(values)
    out = [values[0]]
    for v in values[1:]:
        if abs(v - out[-1]) > tol:
            out.append(v)
    return out


def _bbox_from_lines(xs: List[float], ys: List[float]) -> Tuple[float, float, float, float]:
    return (min(xs), min(ys), max(xs), max(ys))


def _fill_cells_from_text(
    layout,
    xs: List[float],
    ys: List[float],
    bbox: Tuple[float, float, float, float],
) -> List[List[str]]:
    # 单元格数量
    col_count = max(0, len(xs) - 1)
    row_count = max(0, len(ys) - 1)
    if col_count == 0 or row_count == 0:
        return []

    # 以“从上到下”为行序
    rows: List[List[List[Tuple[float, float, str]]]] = [
        [[[] for _ in range(col_count)] for _ in range(row_count)]
    ][0]

    x1, y1, x2, y2 = bbox
    pad = 1e-2
    # 查询范围内文字
    for e in layout.query("TEXT MTEXT"):
        p = _text_anchor_point(e)
        if p is None:
            continue
        x, y = float(p.x), float(p.y)
        if x < x1 - pad or x > x2 + pad or y < y1 - pad or y > y2 + pad:
            continue

        r, c = _locate_cell(x, y, xs, ys)
        if r is None or c is None:
            continue

        txt = _entity_text(e)
        txt = _clean_cell_text(txt)
        if not txt:
            continue

        rows[r][c].append((x, y, txt))

    # 合并每格内容
    out: List[List[str]] = []
    for r in range(row_count):
        out_row: List[str] = []
        for c in range(col_count):
            items = rows[r][c]
            if not items:
                out_row.append("")
                continue
            # 按 y 从高到低、x 从左到右排序，拼接
            items.sort(key=lambda t: (-t[1], t[0]))
            merged = "\n".join(t[2] for t in items)
            out_row.append(merged.strip())
        out.append(out_row)

    return out


def _text_anchor_point(entity) -> Optional[Vec3]:
    try:
        return entity.dxf.insert
    except Exception:  # noqa: BLE001
        return None


def _entity_text(entity) -> str:
    # TEXT: dxf.text; MTEXT: .text（可能含格式）
    if entity.dxftype() == "TEXT":
        return getattr(entity.dxf, "text", "") or ""
    if entity.dxftype() == "MTEXT":
        return getattr(entity, "text", "") or ""
    return ""


def _locate_cell(x: float, y: float, xs: List[float], ys: List[float]) -> Tuple[Optional[int], Optional[int]]:
    # 找列：xs 升序
    c = None
    for i in range(len(xs) - 1):
        if xs[i] - _GRID_TOL <= x <= xs[i + 1] + _GRID_TOL:
            c = i
            break

    # 找行：ys 升序，但我们要 top-down
    r = None
    for k in range(len(ys) - 1):
        if ys[k] - _GRID_TOL <= y <= ys[k + 1] + _GRID_TOL:
            # k=0 表示最底部区间；转换为从上到下
            r = (len(ys) - 2) - k
            break

    return r, c


def _split_title_and_data_drawn(rows: List[List[str]], layout_name: str, index: int) -> tuple[str, List[List[str]]]:
    if not rows:
        return f"{layout_name}_Table{index}", []

    first_row = rows[0]
    non_empty = [cell.strip() for cell in first_row if cell and cell.strip()]

    # 线段拼表格：通常标题是合并单元格 -> 首行仅 1 个非空
    if len(non_empty) == 1:
        return non_empty[0], rows[1:]

    return f"{layout_name}_Table{index}", rows


@dataclass(frozen=True)
class _Grid:
    xs: List[float]
    ys: List[float]
    v_present: List[List[bool]]  # v_present[row][k] for boundary at xs[k], between row's y-interval
    h_present: List[List[bool]]  # h_present[k][col] for boundary at ys[k], between col's x-interval


def _build_grid(cluster: List[_Seg], xs: List[float], ys: List[float]) -> _Grid:
    # row_count: y-intervals
    row_count = len(ys) - 1
    col_count = len(xs) - 1
    # v boundaries at each x line index k in [0..len(xs)-1] for each row interval
    v_present = [[False for _ in range(len(xs))] for _ in range(row_count)]
    # h boundaries at each y line index k in [0..len(ys)-1] for each col interval
    h_present = [[False for _ in range(col_count)] for _ in range(len(ys))]

    def near(a: float, b: float, tol: float = 1e-2) -> bool:
        return abs(a - b) <= tol

    def covers(a1: float, a2: float, b1: float, b2: float, tol: float = 1e-2) -> bool:
        lo = min(a1, a2)
        hi = max(a1, a2)
        return lo <= b1 + tol and hi >= b2 - tol

    for s in cluster:
        if s.orient == "V":
            # match x index
            k = None
            for i, xv in enumerate(xs):
                if near(s.x1, xv):
                    k = i
                    break
            if k is None:
                continue
            for r in range(row_count):
                ylo, yhi = ys[r], ys[r + 1]
                if covers(s.y1, s.y2, ylo, yhi):
                    # r is bottom-up; our text rows are top-down, conversion later is handled by merge mapping
                    v_present[r][k] = True
        else:
            k = None
            for i, yv in enumerate(ys):
                if near(s.y1, yv):
                    k = i
                    break
            if k is None:
                continue
            for c in range(col_count):
                xlo, xhi = xs[c], xs[c + 1]
                if covers(s.x1, s.x2, xlo, xhi):
                    h_present[k][c] = True

    return _Grid(xs=xs, ys=ys, v_present=v_present, h_present=h_present)


def _apply_merges_for_drawn_table(
    rows_topdown: List[List[str]],
    grid: _Grid,
) -> Tuple[List[Tuple[int, int, int, int]], List[List[str]]]:
    row_count = len(rows_topdown)
    col_count = len(rows_topdown[0]) if rows_topdown else 0
    if row_count == 0 or col_count == 0:
        return [], rows_topdown

    # union-find over cells
    parent = list(range(row_count * col_count))

    def idx(r: int, c: int) -> int:
        return r * col_count + c

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # Determine internal boundary presence per top-down row.
    # grid.v_present is bottom-up row intervals; convert:
    # bottom-up r_b = 0 is lowest interval; top-down r_t = row_count-1 - r_b
    def v_boundary_exists(r_t: int, k: int) -> bool:
        r_b = (row_count - 1) - r_t
        return grid.v_present[r_b][k]

    def h_boundary_exists(k: int, c: int) -> bool:
        # k is y line index; presence doesn't depend on row
        return grid.h_present[k][c]

    # Horizontal merges: missing vertical boundary between c and c+1 at xs[c+1]
    for r in range(row_count):
        for c in range(col_count - 1):
            boundary_k = c + 1
            if not v_boundary_exists(r, boundary_k):
                union(idx(r, c), idx(r, c + 1))

    # Vertical merges: missing horizontal boundary between r and r+1 at some y line.
    # rows_topdown r=0 is top interval between ys[-2]..ys[-1]; boundary between r and r+1 corresponds to y line at ys[len(ys)-2 - r]
    for r in range(row_count - 1):
        yline_k = (len(grid.ys) - 2) - r  # between r and r+1
        for c in range(col_count):
            if not h_boundary_exists(yline_k, c):
                union(idx(r, c), idx(r + 1, c))

    # collect components
    comps: Dict[int, List[Tuple[int, int]]] = {}
    for r in range(row_count):
        for c in range(col_count):
            root = find(idx(r, c))
            comps.setdefault(root, []).append((r, c))

    merges: List[Tuple[int, int, int, int]] = []
    normalized = [row[:] for row in rows_topdown]

    for cells in comps.values():
        if len(cells) <= 1:
            continue
        r1 = min(r for r, _ in cells)
        r2 = max(r for r, _ in cells)
        c1 = min(c for _, c in cells)
        c2 = max(c for _, c in cells)
        merges.append((r1, c1, r2, c2))

        # merge text into top-left cell
        texts: List[str] = []
        for r, c in sorted(cells, key=lambda t: (t[0], t[1])):
            v = normalized[r][c].strip()
            if v:
                texts.append(v)
            if (r, c) != (r1, c1):
                normalized[r][c] = ""
        normalized[r1][c1] = "\n".join(texts).strip()

    return merges, normalized


def _split_title_and_data_drawn_with_offset(
    rows: List[List[str]], layout_name: str, index: int
) -> Tuple[str, List[List[str]], int]:
    if not rows:
        return f"{layout_name}_Table{index}", [], 0
    first_row = rows[0]
    non_empty = [cell.strip() for cell in first_row if cell and cell.strip()]
    if len(non_empty) == 1 and _looks_like_header_row(rows[1] if len(rows) > 1 else []):
        return non_empty[0], rows[1:], 1
    return f"{layout_name}_Table{index}", rows, 0


def _shift_merges_row(merges: List[Tuple[int, int, int, int]], delta: int) -> List[Tuple[int, int, int, int]]:
    if delta == 0:
        return merges
    out: List[Tuple[int, int, int, int]] = []
    for r1, c1, r2, c2 in merges:
        nr1 = r1 + delta
        nr2 = r2 + delta
        # 标题行剔除后，可能有 merge 落在负行号，直接丢弃
        if nr2 < 0:
            continue
        nr1 = max(nr1, 0)
        out.append((nr1, c1, nr2, c2))
    return out

