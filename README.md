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

- `main.py`：命令行入口
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

使用方法
--------

### 基本用法

1. 准备一个目录，里面放 DWG/DXF 文件，例如：

   ```text
   C:\Users\Admin\Desktop\dwg\
   ```

2. 在项目根目录运行：

   ```bash
   conda activate dwg-table-exporter
   cd /d D:\GitHub\dwg-table-exporter

   python main.py ^
       --dxf-dir C:\Users\Admin\Desktop\dwg ^
       --output-dir C:\Users\Admin\Desktop\excel_out ^
       --recursive ^
       --overwrite
   ```

参数说明：

- `--dxf-dir`：DWG/DXF 所在根目录，支持同时存在 `.dwg` 和 `.dxf`；
- `--output-dir`：Excel 输出目录，不存在会自动创建；
- `--recursive`：递归遍历子目录（可选）；
- `--overwrite`：若目标 Excel 已存在则覆盖（可选）。

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

已知限制
--------

- 若线段表格的网格线存在大量断点/不对齐，可能会影响识别与合并判断，需要调容差或按图层过滤（后续可加）。
- 依赖 ODA File Converter 解析 DWG，如未安装或配置失败，将只能处理 DXF。

许可证
------

本项目使用仓库根目录中的 `LICENSE` 所述许可证。
