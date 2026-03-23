#!/usr/bin/env sh
# Start API via PYTHONPATH without pip install -e . (run from repo root)
ROOT=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONPATH="$ROOT/src"
cd "$ROOT" || exit 1
exec python -m uvicorn masc_ahu_dwg2excel_api.api:app --host 0.0.0.0 --port 8000 "$@"
