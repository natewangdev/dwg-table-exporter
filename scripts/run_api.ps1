# Start API via PYTHONPATH without pip install -e . (run from repo root)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $root "src"
Set-Location $root
python -m uvicorn masc_ahu_dwg2excel_api.api:app --host 0.0.0.0 --port 8000 @args
