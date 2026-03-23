# masc-ahu-dwg2excel-api

[中文文档](README.zh-CN.md)

Export tables from AutoCAD DWG/DXF files to Excel, powered by Python + ezdxf + openpyxl (HTTP API + CLI).

- DWG/DXF → Excel (`.xlsx`), one Sheet per table
- Supports standard `ACAD_TABLE` and tables drawn with lines + text
- Merged cells, auto column width / row height
- `.dwg` files are converted to DXF via ODA File Converter; `.dxf` files are read directly

## Quick Start

### Local Installation

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
pip install -e ".[dev]"         # includes pytest; or just pip install -e .
```

### Configure ODA File Converter (required for DWG)

1. Download and install from the [ODA website](https://www.opendesign.com/guestfiles/oda_file_converter).
2. Create `ezdxf.ini` in the project root:

```ini
[odafc-addon]
win_exec_path = "D:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe"
unix_exec_path =
```

3. Verify: `python -c "from ezdxf.addons import odafc; print(odafc.is_installed())"` → `True`

> ODA is not needed if you only work with `.dxf` files.

### Start the API

```bash
uvicorn masc_ahu_dwg2excel_api.api:app --host 0.0.0.0 --port 8077
```

- `/healthz` — Health check
- `/docs` — Swagger docs
- `/ui/` — Web test page (upload DWG/DXF, download Excel)

### CLI

```bash
masc-ahu-dwg2excel --dxf-dir /path/to/dwg --output-dir /path/to/excel --recursive --overwrite
```

<details>
<summary>CLI options</summary>

| Option | Description |
|--------|-------------|
| `--dxf-dir` | Root directory containing DWG/DXF files |
| `--output-dir` | Excel output directory (created automatically) |
| `--recursive` | Recurse into subdirectories |
| `--overwrite` | Overwrite existing Excel files |
| `--no-autosize` | Disable auto column width / row height |
| `--dry-run` | Detect and report only, no files written |

</details>

## API

**`POST /export`** (`multipart/form-data`)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `files` | file[] | *required* | One or more DWG/DXF files |
| `autosize` | bool | `true` | Auto column width / row height |
| `min_col_width` | float | `8.0` | Minimum column width |
| `max_col_width` | float | `60.0` | Maximum column width |
| `base_row_height` | float | `15.0` | Base row height |

- Single file → returns `.xlsx`
- Multiple files → returns `.zip` (multiple `.xlsx` + `export_report.json`)

```bash
curl -X POST "http://127.0.0.1:8077/export" \
  -F "files=@/path/to/a.dwg" \
  -F "files=@/path/to/b.dxf" \
  -o result.zip
```

## Docker

### Build

```bash
docker build -t masc-ahu-dwg2excel-api:latest .
```

ODA File Converter is downloaded and installed automatically during build. To specify a version:

```bash
docker build \
  --build-arg ODA_DEB_URL="https://www.opendesign.com/guestfiles/get?filename=ODAFileConverter_QT6_lnxX64_8.3dll_27.1.deb" \
  --build-arg ODA_BUNDLE_SUBDIR=ODAFileConverter_27.1.0.0 \
  -t masc-ahu-dwg2excel-api:latest .
```

### Run

```bash
docker run --rm -d --name masc-ahu-dwg2excel-api -p 8077:80 masc-ahu-dwg2excel-api:latest
```

## Known Limitations

- Drawn-table recognition depends on grid-line completeness; gaps or offsets may require parameter tuning
- `.dwg` parsing requires ODA File Converter; only `.dxf` is supported without it

## License

[MIT](LICENSE)
