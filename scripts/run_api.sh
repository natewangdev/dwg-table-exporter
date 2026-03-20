#!/usr/bin/env sh
# 在未执行 pip install -e . 时，通过 PYTHONPATH 启动 API（仓库根目录下执行）
ROOT=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONPATH="$ROOT/src"
cd "$ROOT" || exit 1
exec python -m uvicorn masc_ahu_dwg2excel_api.api:app --host 0.0.0.0 --port 8000 "$@"
