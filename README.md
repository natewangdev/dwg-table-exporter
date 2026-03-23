# masc-ahu-dwg2excel-api

基于 Python + ezdxf + openpyxl 的 **AutoCAD 表格数据导出**（HTTP API + CLI）。

- DWG/DXF → Excel（`.xlsx`），每个表格一个 Sheet
- 支持标准 `ACAD_TABLE` 和"线段 + 文字"拼出的表格
- 支持合并单元格、自动列宽行高
- `.dwg` 通过 ODA File Converter 转为 DXF 后解析；`.dxf` 直接处理

## 快速开始

### 本地安装

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
pip install -e ".[dev]"         # 含 pytest；或 pip install -e .
```

### 配置 ODA File Converter（处理 DWG 必需）

1. 从 [ODA 官网](https://www.opendesign.com/guestfiles/oda_file_converter) 下载安装。
2. 在项目根目录创建 `ezdxf.ini`：

```ini
[odafc-addon]
win_exec_path = "D:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe"
unix_exec_path =
```

3. 验证：`python -c "from ezdxf.addons import odafc; print(odafc.is_installed())"` → `True`

> 仅处理 `.dxf` 文件时无需安装 ODA。

### 启动 API

```bash
uvicorn masc_ahu_dwg2excel_api.api:app --host 0.0.0.0 --port 8077
```

- `/healthz` — 健康检查
- `/docs` — Swagger 文档
- `/ui/` — Web 测试页（上传 DWG/DXF，下载 Excel）

### CLI

```bash
masc-ahu-dwg2excel --dxf-dir /path/to/dwg --output-dir /path/to/excel --recursive --overwrite
```

<details>
<summary>CLI 参数说明</summary>

| 参数 | 说明 |
|------|------|
| `--dxf-dir` | DWG/DXF 所在根目录 |
| `--output-dir` | Excel 输出目录（自动创建） |
| `--recursive` | 递归遍历子目录 |
| `--overwrite` | 覆盖已有 Excel |
| `--no-autosize` | 禁用自动列宽/行高 |
| `--dry-run` | 只识别统计，不写出文件 |

</details>

## API 接口

**`POST /export`**（`multipart/form-data`）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `files` | file[] | *必填* | 一个或多个 DWG/DXF 文件 |
| `autosize` | bool | `true` | 自动列宽/行高 |
| `min_col_width` | float | `8.0` | 最小列宽 |
| `max_col_width` | float | `60.0` | 最大列宽 |
| `base_row_height` | float | `15.0` | 基础行高 |

- 单文件 → 返回 `.xlsx`
- 多文件 → 返回 `.zip`（含多个 `.xlsx` + `export_report.json`）

```bash
curl -X POST "http://127.0.0.1:8077/export" \
  -F "files=@/path/to/a.dwg" \
  -F "files=@/path/to/b.dxf" \
  -o result.zip
```

## Docker

### 构建镜像

```bash
docker build -t masc-ahu-dwg2excel-api:latest .
```

ODA File Converter 在构建阶段自动下载安装。若需指定版本：

```bash
docker build \
  --build-arg ODA_DEB_URL="https://www.opendesign.com/guestfiles/get?filename=ODAFileConverter_QT6_lnxX64_8.3dll_27.1.deb" \
  --build-arg ODA_BUNDLE_SUBDIR=ODAFileConverter_27.1.0.0 \
  -t masc-ahu-dwg2excel-api:latest .
```

### 启动容器

```bash
docker run --rm -d --name masc-ahu-dwg2excel-api -p 8077:8077 masc-ahu-dwg2excel-api:latest
```

## 已知限制

- 线段表格识别依赖网格线完整度，断点/偏移可能需要调参
- `.dwg` 解析依赖 ODA File Converter，未配置时仅能处理 `.dxf`
