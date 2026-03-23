#!/usr/bin/env sh
set -eu

# ODAFC_EXEC_PATH is set at build time; can be overridden at runtime via -e.
if [ -n "${ODAFC_EXEC_PATH:-}" ]; then
  cat > /app/ezdxf.ini <<EOF
[odafc-addon]
win_exec_path =
unix_exec_path = "${ODAFC_EXEC_PATH}"
EOF
fi

PORT="${PORT:-80}"
echo "[entrypoint] Starting API on 0.0.0.0:${PORT} (PYTHONUNBUFFERED=${PYTHONUNBUFFERED:-})"

# Qt runtime directory required by ODA File Converter
export XDG_RUNTIME_DIR=/tmp/runtime-root
mkdir -p "$XDG_RUNTIME_DIR" && chmod 0700 "$XDG_RUNTIME_DIR"

# Virtual X display for ODA File Converter (Qt GUI that requires DISPLAY).
# Avoid xvfb-run: slim image lacks xdpyinfo, causing its readiness check to hang.
export DISPLAY=:99
Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp &
sleep 1

exec python -u -m uvicorn masc_ahu_dwg2excel_api.api:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --log-level info \
  --access-log
