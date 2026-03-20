masc-ahu-dwg2excel-api
======================

基于 Python + ezdxf + openpyxl 的 **AutoCAD 表格数据导出**（HTTP API + 可选 CLI）：

- 一个 DWG/DXF → 一个 Excel 文件（`.xlsx`）
- 图中每个表格 → 一个 Sheet（支持标准 `ACAD_TABLE`，也支持“线段+文字”拼出来的表格）
- Sheet 名为表格标题行（如“能耗”等）
- Sheet 中不包含标题行，只包含真实数据行
- 支持合并单元格导出（Excel 中真实 `merge`）
- 单元格默认全边框；合并单元格默认水平/垂直居中

> 提示：线段表格的识别依赖“网格线完整度”和几何容差，若你的表格线有断点/偏移，可能需要调参。

项目结构（常见 Python API 仓库布局）
------------------------------------

```text
.
├── pyproject.toml          # 项目元数据与依赖（包名 masc-ahu-dwg2excel-api）
├── requirements.txt        # 与 pyproject 对齐的运行依赖（便于 Docker/CI）
├── Dockerfile
├── docker-entrypoint.sh
├── docker/oda/             # 构建镜像前放入 ODA（见该目录说明，通常不提交二进制）
├── src/masc_ahu_dwg2excel_api/
│   ├── api.py              # FastAPI 应用（/export、/healthz、/ui）
│   ├── cli.py              # Click 命令行入口
│   ├── config.py
│   ├── pipeline.py
│   ├── dxf_reader.py
│   ├── io_loader.py
│   ├── static/index.html   # 简易 API 测试页
│   └── ...                 # 读表、写 Excel 等模块
├── tests/                  # pytest
├── scripts/                # run_api.ps1 / run_api.sh（不设 PYTHONPATH 时可用）
├── README.md
└── LICENSE
```

环境准备
--------

### 1. 安装

**注意：** 仅执行 `pip install -r requirements.txt` **不会**安装本仓库里的包，`uvicorn masc_ahu_dwg2excel_api...` 会报 `ModuleNotFoundError`。必须在项目根目录再执行一次 **`pip install -e .`**（或可编辑开发依赖 `pip install -e ".[dev]"`）。

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -U pip
pip install -r requirements.txt
pip install -e ".[dev]"   # 或 pip install -e .（不含 pytest 可选依赖）
```

控制台脚本（**在 `pip install -e .` 之后**）：`masc-ahu-dwg2excel`（见 `pyproject.toml` 的 `[project.scripts]`）。

**不入库安装、仅想快速起服务：** 可把 `src` 加入 `PYTHONPATH`，或使用仓库内脚本：

- Windows PowerShell（项目根目录）：`powershell -ExecutionPolicy Bypass -File scripts/run_api.ps1`
- Linux/macOS：`chmod +x scripts/run_api.sh && ./scripts/run_api.sh`

### 2. 安装 ODA File Converter（用于 DWG → DXF）

1. 从 ODA 官网下载安装 **ODA File Converter**。  
2. Windows 示例路径：

   ```text
   D:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe
   ```

3. 在项目根目录（本仓库根目录）创建或编辑 `ezdxf.ini`：

   ```ini
   [odafc-addon]
   win_exec_path = "D:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe"
   unix_exec_path =
   ```

4. 测试 ODA 是否可用：

   ```bash
   python -c "from ezdxf.addons import odafc; print(odafc.is_installed())"
   ```

   输出 `True` 表示配置成功。

> 如果只处理 DXF 文件，可以不安装 ODA。

开发与测试
----------

```bash
pytest -q
```

使用方法（API）
---------------

### 1. 启动 API 服务

先完成上节 **`pip install -e .`**。然后：

```bash
uvicorn masc_ahu_dwg2excel_api.api:app --host 0.0.0.0 --port 8000
```

若仍提示 `No module named 'masc_ahu_dwg2excel_api'`，确认当前目录为仓库根目录且已激活安装所用的虚拟环境，并重新执行 `pip install -e .`。

服务启动后，可访问：

- `http://127.0.0.1:8000/healthz`：健康检查
- `http://127.0.0.1:8000/docs`：Swagger 文档
- `http://127.0.0.1:8000/ui/`：简易 Web 测试页（上传 DWG/DXF，下载 Excel / ZIP）

### 2. 调用导出接口

接口：`POST /export`（`multipart/form-data`）

- `files`：一个或多个 `dwg/dxf` 文件（必填）
- `autosize`：是否自动列宽/行高（默认 `true`）
- `min_col_width`：最小列宽（默认 `8.0`）
- `max_col_width`：最大列宽（默认 `60.0`）
- `base_row_height`：基础行高（默认 `15.0`）

返回：

- 上传 1 个文件：直接返回 1 个 `.xlsx`
- 上传多个文件：返回 `exported_excels.zip`（包含多个 `.xlsx` 和 `export_report.json`）

示例（Linux/macOS）：

```bash
curl -X POST "http://127.0.0.1:8000/export" \
  -F "files=@/path/to/a.dwg" \
  -F "files=@/path/to/b.dxf" \
  -F "autosize=true" \
  -F "min_col_width=8" \
  -F "max_col_width=60" \
  -F "base_row_height=15" \
  -o result.zip
```

### 3. ODA 可执行路径（DWG 必需）

当处理 `.dwg` 时，必须保证 ODA File Converter 可用，可通过两种方式配置：

1. `ezdxf.ini`（节选）：

   ```ini
   [odafc-addon]
   win_exec_path = "D:\\Program Files\\ODA\\ODAFileConverter 27.1.0\\ODAFileConverter.exe"
   unix_exec_path = "/opt/oda/usr/bin/ODAFileConverter"
   ```

2. 环境变量（优先）：`ODAFC_EXEC_PATH`

> 若 ODA 不可用，`.dwg` 会返回明确错误；`.dxf` 不受影响。

Docker 运行
-----------

### 1. 将 ODA File Converter 放入构建上下文

镜像构建时会将 **Linux 版** ODA File Converter 打包进镜像（不再依赖运行时挂载）。

**推荐：与 Debian/Ubuntu 官方 `.deb` 相同的目录结构**（与 `Dockerfile` 默认值一致）。

在已安装 `odafileconverter` 的机器上，于**项目仓库根目录**执行：

```bash
mkdir -p docker/oda/usr/bin
cp -a /usr/bin/ODAFileConverter docker/oda/usr/bin/
cp -a /usr/bin/ODAFileConverter_27.1.0.0 docker/oda/usr/bin/
```

说明：

- 必须同时包含启动入口 **`ODAFileConverter`** 与 **`ODAFileConverter_<版本>/` 整目录**（内有 `lib/`、`plugins/`、`qt.conf` 等）。
- 若你本机版本目录不是 `ODAFileConverter_27.1.0.0`，先执行  
  `dpkg -L odafileconverter | grep ODAFileConverter_` 确认目录名；构建时用  
  `--build-arg ODA_BUNDLE=usr/bin/ODAFileConverter_x.x.x.x` 指定。
- 详情见 [docker/oda/README.md](docker/oda/README.md)。

### 2. 构建镜像

默认已设置 `ODA_BINARY=usr/bin/ODAFileConverter`、`ODA_BUNDLE=usr/bin/ODAFileConverter_27.1.0.0`，并配置 `LD_LIBRARY_PATH`、`QT_PLUGIN_PATH`：

```bash
docker build -t masc-ahu-dwg2excel-api:latest .
```

版本目录名不同时示例：

```bash
docker build \
  --build-arg ODA_BUNDLE=usr/bin/ODAFileConverter_27.1.0.0 \
  -t masc-ahu-dwg2excel-api:latest .
```

### 3. 启动容器

```bash
docker run --rm -p 8000:8000 masc-ahu-dwg2excel-api:latest
```

可选：运行时覆盖 ODA 可执行路径（一般无需；若改路径，请同步保证 bundle 与库路径仍正确）：

```bash
docker run --rm -p 8000:8000 \
  -e ODAFC_EXEC_PATH=/opt/oda/usr/bin/ODAFileConverter \
  masc-ahu-dwg2excel-api:latest
```

说明：

- 镜像内通过 `pip install .` 安装 `masc_ahu_dwg2excel_api`，入口为 `uvicorn masc_ahu_dwg2excel_api.api:app`。
- 镜像包含 `xvfb`（无头环境）与打包的 ODA 程序；`Dockerfile` 会校验可执行文件与 bundle 目录。
- `docker/oda` 中的二进制默认不纳入 Git（见 `.gitignore`）。

使用方法（命令行）
------------------

安装项目后，使用入口脚本 **`masc-ahu-dwg2excel`**，或：

```bash
python -m masc_ahu_dwg2excel_api.cli --dxf-dir /path/to/dwg --output-dir /path/to/excel --recursive --overwrite
```

Windows 示例：

```text
masc-ahu-dwg2excel --dxf-dir D:\data\dwg --output-dir D:\data\excel --recursive --overwrite
```

参数说明：

- `--dxf-dir`：DWG/DXF 所在根目录，支持同时存在 `.dwg` 和 `.dxf`；
- `--output-dir`：Excel 输出目录，不存在会自动创建；
- `--recursive`：递归遍历子目录（可选）；
- `--overwrite`：若目标 Excel 已存在则覆盖（可选）；
- `--autosize/--no-autosize`：是否自动调整列宽/行高（默认开启）；
- `--dry-run`：只识别/统计，不写出 Excel（用于调试识别效果）。

导出规则
--------

- **文件级**：  
  - 每个 `*.dwg` / `*.dxf` 对应一个同名 `*.xlsx` 文件。  
  - `.dwg` 会通过 ODA 转换为临时 DXF 再由 ezdxf 解析。

- **表格级（ACAD_TABLE）**：  
  - 遍历每个布局（模型空间 + 纸空间）的 `ACAD_TABLE` 实体。  
  - 对表格内容调用 `read_acad_table_content()` 获取二维字符串数组。  
  - 对每一个单元格：移除 MTEXT 格式码、处理换行、去空白等。

- **表格级（线段+文字拼表格）**：  
  - 扫描水平/垂直线段重建网格；将 `TEXT/MTEXT` 归入单元格；支持合并单元格导出。

- **标题与 Sheet 名（通用）**：  
  - 首行单标题 + 下一行多列表头时，首行为标题（不写入 Excel），否则整表写入。

- **过滤规则**：  
  - 剔除空表；线段表过滤 1×1 网格等误识别。

日志与调试
---------

- 每个文件处理后输出统计：`total` / `acad_table` / `drawn` / `skipped` 等。

已知限制
--------

- 线段表格对网格完整度敏感，可能需要调参。
- 解析 DWG 依赖 ODA File Converter；未配置时只能稳定处理 DXF。

许可证
------

本项目使用仓库根目录中的 `LICENSE` 所述许可证。
