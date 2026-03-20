dwg-table-exporter
==================

基于 Python + ezdxf + openpyxl 的 **AutoCAD 表格数据批量导出工具**：

- 一个 DWG/DXF → 一个 Excel 文件（`.xlsx`）
- 图中每个表格 → 一个 Sheet（支持标准 `ACAD_TABLE`，也支持“线段+文字”拼出来的表格）
- Sheet 名为表格标题行（如“能耗”等）
- Sheet 中不包含标题行，只包含真实数据行
- 支持合并单元格导出（Excel 中真实 `merge`）
- 单元格默认全边框；合并单元格默认水平/垂直居中

> 提示：线段表格的识别依赖“网格线完整度”和几何容差，若你的表格线有断点/偏移，可能需要调参。

目录结构
--------

- `main.py`：命令行入口（兼容保留）
- `dwg_table_exporter/api.py`：FastAPI 服务入口（推荐）
- `dwg_table_exporter/config.py`：导出配置
- `dwg_table_exporter/dxf_reader.py`：对外门面（查找文件、读取表格）
- `dwg_table_exporter/io_loader.py`：DWG/DXF 加载（含 ODAFileConverter）
- `dwg_table_exporter/text_clean.py`：单元格文本清洗（去 MTEXT 格式码）
- `dwg_table_exporter/title_rules.py`：标题/表头判定规则
- `dwg_table_exporter/acad_table_reader.py`：标准 `ACAD_TABLE` 解析
- `dwg_table_exporter/drawn_table_reader.py`：线段+文字表格解析（含合并单元格）
- `dwg_table_exporter/excel_writer.py`：Excel 写入
- `dwg_table_exporter/pipeline.py`：批量处理流程
- `requirements.txt`：Python 依赖
- `docker/oda/`：构建 Docker 镜像时放入 Linux 版 ODA File Converter（见该目录下说明）
- `static/index.html`：API 测试页（挂载路径 `/ui/`）

环境准备
--------

### 1. 创建 Conda 环境（推荐）

```bash
conda create -n dwg-table-exporter python=3.10
conda activate dwg-table-exporter
pip install -r requirements.txt
```

### 2. 安装 ODA File Converter（用于 DWG → DXF）

1. 从 ODA 官网下载安装 **ODA File Converter**。  
2. 假设安装在：

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

> 如果只处理 DXF 文件，可以不安装 ODA，此时程序会忽略 `.dwg`。

使用方法（API）
---------------

### 1. 启动 API 服务

```bash
pip install -r requirements.txt
uvicorn dwg_table_exporter.api:app --host 0.0.0.0 --port 8000
```

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

1. `ezdxf.ini`：

   ```ini
   [odafc-addon]
   win_exec_path = "D:\\Program Files\\ODA\\ODAFileConverter 27.1.0\\ODAFileConverter.exe"
   unix_exec_path = "/opt/ODA/ODAFileConverter"
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
docker build -t dwg-table-exporter:latest .
```

版本目录名不同时示例：

```bash
docker build \
  --build-arg ODA_BUNDLE=usr/bin/ODAFileConverter_27.1.0.0 \
  -t dwg-table-exporter:latest .
```

### 3. 启动容器

```bash
docker run --rm -p 8000:8000 dwg-table-exporter:latest
```

可选：运行时覆盖 ODA 可执行路径（一般无需；若改路径，请同步保证 bundle 与库路径仍正确）：

```bash
docker run --rm -p 8000:8000 \
  -e ODAFC_EXEC_PATH=/opt/oda/usr/bin/ODAFileConverter \
  dwg-table-exporter:latest
```

说明：

- 镜像内包含 API、`xvfb`（无头环境）以及构建时复制的 ODA 程序；`Dockerfile` 会校验可执行文件与 bundle 目录是否存在。
- `docker/oda` 中的二进制默认不纳入 Git（见 `.gitignore`），由你在本地或 CI 中放入后再构建。
- 容器启动后可直接调用 `POST /export` 进行导出。

使用方法（命令行，兼容保留）
--------------------------

### 基本用法

1. 准备一个目录，里面放 DWG/DXF 文件，例如：

   ```text
   C:\Users\Admin\Desktop\dwg\
   ```

2. 在项目根目录运行：

   ```bash
   conda activate dwg-table-exporter
   cd /d D:\GitHub\dwg-table-exporter

   python main.py --dxf-dir C:\Users\WangHaij\Desktop\dwg --output-dir C:\Users\WangHaij\Desktop\excel --recursive --overwrite
   ```

参数说明：

- `--dxf-dir`：DWG/DXF 所在根目录，支持同时存在 `.dwg` 和 `.dxf`；
- `--output-dir`：Excel 输出目录，不存在会自动创建；
- `--recursive`：递归遍历子目录（可选）；
- `--overwrite`：若目标 Excel 已存在则覆盖（可选）。
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
  - 对每一个单元格：
    - 移除 MTEXT 字体与格式代码，例如 `{\fSimSun|b0|i0|c134|p2;`、`\L`、`\H1.0;` 等；
    - 处理 `\P`、`\n` 为换行；
    - 去掉多余 `{`、`}`，做去空白；
    - 例如：`{\fSimSun|b0|i0|c134|p2;列}1` → `列1`。

- **表格级（线段+文字拼表格）**：
  - 扫描水平/垂直线段（`LINE/LWPOLYLINE/POLYLINE`）重建网格；
  - 将 `TEXT/MTEXT` 按坐标归入单元格；
  - 识别缺失内部边界线，导出为 Excel 合并单元格；
  - 合并区域文字汇总到左上角单元格。

- **标题与 Sheet 名（通用）**：
  - 仅当“首行只有 1 个非空单元格”且“下一行至少 2 个非空单元格（更像表头）”时，才把首行当作 **表格标题**：
    - Sheet 名 = 标题文本；
    - 标题行不写入 Excel；
  - 否则 Sheet 名退回为 `布局名_Table序号`，整表写入。

- **过滤规则**：
  - 剔除导出内容为空的表格（包含剔除标题行后为空的情况）；
  - 对“线段+文字”表格：
    - 过滤 1×1 网格（常见图框/标题栏矩形）；
    - 过滤仅 1 个非空单元格的伪表格（常见图纸总标题误识别）。

日志与调试
---------

- 每个文件处理后都会输出统计信息：
  - `total`：可导出的表总数
  - `acad_table`：标准 `ACAD_TABLE` 导出数量
  - `drawn`：线段+文字表格导出数量
  - `skipped`：跳过原因计数（如 `empty_table`, `grid_1x1`, `only_one_non_empty_cell`, `no_text_in_grid` 等）
- 若线段表格解析发生异常，错误信息会包含 `file/layout/bbox/grid` 等上下文，便于定位复现。

已知限制
--------

- 若线段表格的网格线存在大量断点/不对齐，可能会影响识别与合并判断，需要调容差或按图层过滤（后续可加）。
- 依赖 ODA File Converter 解析 DWG，如未安装或配置失败，将只能处理 DXF。

许可证
------

本项目使用仓库根目录中的 `LICENSE` 所述许可证。
