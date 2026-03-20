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
├── Dockerfile              # 构建时下载并安装 ODA File Converter .deb
├── docker-entrypoint.sh
├── .github/workflows/      # CI：main 推送构建镜像并上传 Artifact
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
   unix_exec_path = "/usr/bin/ODAFileConverter"
   ```

2. 环境变量（优先）：`ODAFC_EXEC_PATH`

> 若 ODA 不可用，`.dwg` 会返回明确错误；`.dxf` 不受影响。

Docker 运行
-----------

### Debian WSL 说明

若你在 **Windows 下的 Debian WSL（WSL2）** 里使用本仓库（未使用 Docker Desktop）：

- 在 Debian 内安装 **Docker Engine**：可与物理机相同按官方文档 *Install Docker Engine on Debian* 配置官方仓库；**快速试用**可用：`sudo apt update && sudo apt install -y docker.io`，再把用户加入 `docker` 组后**重开终端**：`sudo usermod -aG docker "$USER"`。`docker` 命令只在 **WSL（Debian）终端**里使用。
- **`--network host`** 与 **`-p 8000:8000`** 在 WSL2 下都可用；`docker ps` 在 host 模式下 **PORTS 为空** 正常。
- **先在同一 WSL 里**执行 `curl -sS http://127.0.0.1:8000/healthz` 确认服务已起来；若在 **Windows 浏览器** 访问，用 `http://localhost:8000` 或 WSL 的 IP（`hostname -I` 取第一个），详见下文「从哪里访问？」。

### 1. 构建镜像

`Dockerfile` 在构建阶段会从 **Open Design Alliance 访客下载页**拉取默认版本的 **Linux `.deb`** 并 `apt` 安装（见文件中 `ODA_DEB_URL`、`ODA_BUNDLE_SUBDIR`）。无需本地 `docker/oda` 目录。

```bash
docker build -t masc-ahu-dwg2excel-api:latest .
```

若官方更新安装包地址或版本，可使用构建参数（示例）：

```bash
docker build \
  --build-arg ODA_DEB_URL="https://www.opendesign.com/guestfiles/get?filename=ODAFileConverter_QT6_lnxX64_8.3dll_27.1.deb" \
  --build-arg ODA_BUNDLE_SUBDIR=ODAFileConverter_27.1.0.0 \
  -t masc-ahu-dwg2excel-api:latest .
```

说明：`ODA_BUNDLE_SUBDIR` 须与 `.deb` 安装后的 **`/usr/bin/ODAFileConverter_<版本>/`** 目录名一致（可在本机安装同款 `.deb` 后执行 `dpkg -L odafileconverter | head` 核对）。

### 2. 启动容器

下面两种任选其一（**在 WSL 里直接安装 Docker Engine、不用 Docker Desktop 时，两者都可用**）。

**方式 A：端口映射（最简单，推荐）**

```bash
docker run --rm --name masc-ahu-dwg2excel-api -p 8000:8000 masc-ahu-dwg2excel-api:latest
```

**方式 B：`--network host`（仅适用于 Linux 内核上的 Docker，例如 WSL2 / 物理 Linux）**

```bash
docker run --rm --network host masc-ahu-dwg2excel-api:latest
```

此时 `docker ps` 里 **PORTS 可能为空** 属正常现象。

**若你用的是 Docker Desktop（Windows/Mac 版）** host 网络**不会**按 Linux 方式工作，请只用上面的 **方式 A**。

---

**从哪里访问？**

| 你在哪操作 | 怎么访问 |
|------------|----------|
| 浏览器 / `curl` 在 **同一 WSL 发行版里** | `http://127.0.0.1:8000/docs` |
| 浏览器在 **Windows**，服务跑在 **WSL 的 Docker** 里 | 先试 `http://localhost:8000/docs`（Win11 常自动转发）；不行则在 WSL 里执行 `hostname -I` 取第一个 IP，在 Windows 浏览器用 `http://<该IP>:8000/docs` |

---

**排查：打不开 /docs、`docker logs` 没什么输出**

1. 先看日志是否出现 **`[entrypoint] Starting API on ...`**（已更新镜像/entrypoint 后）；没有则确认用的是新构建的镜像。  
2. 在 **WSL 终端**（与 `docker` 同一环境）执行：`curl -sS http://127.0.0.1:8000/healthz`。  
3. 若用方式 A，进容器：`docker exec -it masc-ahu-dwg2excel-api curl -sS http://127.0.0.1:8000/healthz`。  
4. 访问 `/docs` 后，`docker logs` 中应有 uvicorn 的 **access** 日志。

镜像内已设置 `ODAFC_EXEC_PATH=/usr/bin/ODAFileConverter` 及 Qt 插件路径。若需覆盖：

```bash
docker run --rm -p 8000:8000 \
  -e ODAFC_EXEC_PATH=/usr/bin/ODAFileConverter \
  masc-ahu-dwg2excel-api:latest
```

### 3. GitHub Actions 与镜像 Artifact

向 **`main`** 分支推送代码时，工作流 [.github/workflows/docker-image.yml](.github/workflows/docker-image.yml) 会：

1. 构建 Docker 镜像  
2. 执行 `docker save` 生成 **`masc-ahu-dwg2excel-api.tar`**  
3. 将 tar 作为 **Artifact** 上传（保留 14 天）

在仓库 **Actions** 标签页打开对应运行结果，在页面底部 **Artifacts** 中即可下载该 tar。本地加载：

```bash
docker load -i masc-ahu-dwg2excel-api.tar
docker run --rm -p 8000:8000 masc-ahu-dwg2excel-api:latest
```

说明：

- 镜像内通过 `pip install .` 安装应用，入口为 `uvicorn masc_ahu_dwg2excel_api.api:app`。
- 访客下载 URL 若变更导致构建失败，请按需更新 `Dockerfile` 中的默认 `ODA_DEB_URL` 或使用上述 `build-arg`。

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
