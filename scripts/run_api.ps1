# 在未执行 pip install -e . 时，通过 PYTHONPATH 启动 API（仓库根目录执行）
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $root "src"
Set-Location $root
python -m uvicorn masc_ahu_dwg2excel_api.api:app --host 0.0.0.0 --port 8000 @args
