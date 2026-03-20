from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .dxf_reader import read_tables_with_report
from .excel_writer import tables_to_workbook
from .reporting import ParseContextError

ALLOWED_SUFFIXES = {".dxf", ".dwg"}

app = FastAPI(title="DWG Table Exporter API", version="1.0.0")

# 便于浏览器本地或其它端口打开测试页时调用 API（生产环境请按需收紧 allow_origins）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_STATIC_DIR), html=True), name="ui")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/export")
async def export_tables(
    files: list[UploadFile] = File(..., description="上传一个或多个 DWG/DXF 文件"),
    autosize: bool = Form(True),
    min_col_width: float = Form(8.0),
    max_col_width: float = Form(60.0),
    base_row_height: float = Form(15.0),
) -> Response:
    if not files:
        raise HTTPException(status_code=400, detail="至少上传一个 DWG 或 DXF 文件。")
    if min_col_width <= 0 or max_col_width <= 0 or base_row_height <= 0:
        raise HTTPException(status_code=400, detail="列宽和行高参数必须大于 0。")
    if min_col_width > max_col_width:
        raise HTTPException(status_code=400, detail="min_col_width 不能大于 max_col_width。")

    with TemporaryDirectory(prefix="dwg-export-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        exported: list[tuple[str, bytes]] = []
        results: list[dict[str, str]] = []

        for upload in files:
            original_name = Path(upload.filename or "").name
            suffix = Path(original_name).suffix.lower()
            if suffix not in ALLOWED_SUFFIXES:
                results.append(
                    {
                        "file": original_name or "<unknown>",
                        "status": "failed",
                        "message": f"不支持的文件类型: {suffix or '<none>'}",
                    }
                )
                continue

            file_name = original_name or f"upload_{len(exported) + len(results) + 1}{suffix}"
            input_path = tmp_root / file_name
            input_path.parent.mkdir(parents=True, exist_ok=True)

            content = await upload.read()
            input_path.write_bytes(content)

            try:
                tables, report = read_tables_with_report(input_path)
                if not tables:
                    results.append({"file": file_name, "status": "failed", "message": "未识别到可导出的表格数据。"})
                    continue

                wb = tables_to_workbook(
                    tables,
                    autosize=autosize,
                    min_col_width=min_col_width,
                    max_col_width=max_col_width,
                    base_row_height=base_row_height,
                )
                stream = io.BytesIO()
                wb.save(stream)
                exported.append((input_path.with_suffix(".xlsx").name, stream.getvalue()))

                skipped_str = ", ".join(f"{k}={v}" for k, v in sorted(report.skipped.items())) if report.skipped else "none"
                results.append(
                    {
                        "file": file_name,
                        "status": "success",
                        "message": (
                            f"total={report.total_exported}, "
                            f"acad_table={report.acad_table_exported}, "
                            f"drawn={report.drawn_table_exported}, "
                            f"skipped={skipped_str}"
                        ),
                    }
                )
            except ParseContextError as exc:
                results.append({"file": file_name, "status": "failed", "message": str(exc)})
            except Exception as exc:  # noqa: BLE001
                results.append({"file": file_name, "status": "failed", "message": str(exc)})

        if not exported:
            raise HTTPException(status_code=422, detail={"message": "没有成功导出任何文件。", "results": results})

        if len(exported) == 1:
            xlsx_name, payload = exported[0]
            return Response(
                content=payload,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{xlsx_name}"'},
            )

        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for xlsx_name, payload in exported:
                zf.writestr(xlsx_name, payload)
            report_payload: dict[str, Any] = {"results": results, "exported_count": len(exported)}
            zf.writestr("export_report.json", json.dumps(report_payload, ensure_ascii=False, indent=2))

        return Response(
            content=zip_stream.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="exported_excels.zip"'},
        )
