from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ezdxf.math import Vec3

from .models import TableData
from .table_filters import has_any_content
from .text_clean import clean_cell_text
from .title_rules import split_title_and_data


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


@dataclass(frozen=True)
class _Grid:
    xs: List[float]
    ys: List[float]
    v_present: List[List[bool]]  # v_present[row][k] for boundary at xs[k], between row's y-interval (bottom-up)
    h_present: List[List[bool]]  # h_present[k][col] for boundary at ys[k], between col's x-interval


def read_drawn_tables_from_layout(layout, *, layout_name: str, start_index: int) -> List[TableData]:
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

        title, data_rows, title_row_offset = split_title_and_data(normalized_rows, layout_name, next_index)
        adj_merges = _shift_merges_row(merges, -title_row_offset)

        if has_any_content(data_rows):
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
    col_count = max(0, len(xs) - 1)
    row_count = max(0, len(ys) - 1)
    if col_count == 0 or row_count == 0:
        return []

    buckets: List[List[List[Tuple[float, float, str]]]] = [[[] for _ in range(col_count)] for _ in range(row_count)]

    x1, y1, x2, y2 = bbox
    pad = 1e-2
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

        txt = clean_cell_text(_entity_text(e))
        if not txt:
            continue

        buckets[r][c].append((x, y, txt))

    out: List[List[str]] = []
    for r in range(row_count):
        out_row: List[str] = []
        for c in range(col_count):
            items = buckets[r][c]
            if not items:
                out_row.append("")
                continue
            items.sort(key=lambda t: (-t[1], t[0]))
            out_row.append("\n".join(t[2] for t in items).strip())
        out.append(out_row)

    return out


def _text_anchor_point(entity) -> Optional[Vec3]:
    try:
        return entity.dxf.insert
    except Exception:  # noqa: BLE001
        return None


def _entity_text(entity) -> str:
    if entity.dxftype() == "TEXT":
        return getattr(entity.dxf, "text", "") or ""
    if entity.dxftype() == "MTEXT":
        return getattr(entity, "text", "") or ""
    return ""


def _locate_cell(x: float, y: float, xs: List[float], ys: List[float]) -> Tuple[Optional[int], Optional[int]]:
    c = None
    for i in range(len(xs) - 1):
        if xs[i] - _GRID_TOL <= x <= xs[i + 1] + _GRID_TOL:
            c = i
            break

    r = None
    for k in range(len(ys) - 1):
        if ys[k] - _GRID_TOL <= y <= ys[k + 1] + _GRID_TOL:
            r = (len(ys) - 2) - k  # bottom-up -> top-down
            break

    return r, c


def _build_grid(cluster: List[_Seg], xs: List[float], ys: List[float]) -> _Grid:
    row_count = len(ys) - 1
    col_count = len(xs) - 1
    v_present = [[False for _ in range(len(xs))] for _ in range(row_count)]
    h_present = [[False for _ in range(col_count)] for _ in range(len(ys))]

    def near(a: float, b: float, tol: float = 1e-2) -> bool:
        return abs(a - b) <= tol

    def covers(a1: float, a2: float, b1: float, b2: float, tol: float = 1e-2) -> bool:
        lo = min(a1, a2)
        hi = max(a1, a2)
        return lo <= b1 + tol and hi >= b2 - tol

    for s in cluster:
        if s.orient == "V":
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

    def v_boundary_exists(r_t: int, k: int) -> bool:
        r_b = (row_count - 1) - r_t
        return grid.v_present[r_b][k]

    def h_boundary_exists(k: int, c: int) -> bool:
        return grid.h_present[k][c]

    for r in range(row_count):
        for c in range(col_count - 1):
            boundary_k = c + 1
            if not v_boundary_exists(r, boundary_k):
                union(idx(r, c), idx(r, c + 1))

    for r in range(row_count - 1):
        yline_k = (len(grid.ys) - 2) - r
        for c in range(col_count):
            if not h_boundary_exists(yline_k, c):
                union(idx(r, c), idx(r + 1, c))

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

        texts: List[str] = []
        for r, c in sorted(cells, key=lambda t: (t[0], t[1])):
            v = normalized[r][c].strip()
            if v:
                texts.append(v)
            if (r, c) != (r1, c1):
                normalized[r][c] = ""
        normalized[r1][c1] = "\n".join(texts).strip()

    return merges, normalized


def _shift_merges_row(merges: List[Tuple[int, int, int, int]], delta: int) -> List[Tuple[int, int, int, int]]:
    if delta == 0:
        return merges
    out: List[Tuple[int, int, int, int]] = []
    for r1, c1, r2, c2 in merges:
        nr1 = r1 + delta
        nr2 = r2 + delta
        if nr2 < 0:
            continue
        nr1 = max(nr1, 0)
        out.append((nr1, c1, nr2, c2))
    return out

