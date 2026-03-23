#!/usr/bin/env sh
set -eu

# 镜像构建时已设置 ODAFC_EXEC_PATH；运行时也允许通过 -e 覆盖。
if [ -n "${ODAFC_EXEC_PATH:-}" ]; then
  cat > /app/ezdxf.ini <<EOF
[odafc-addon]
win_exec_path =
unix_exec_path = "${ODAFC_EXEC_PATH}"
EOF
fi

PORT="${PORT:-8077}"
echo "[entrypoint] Starting API on 0.0.0.0:${PORT} (PYTHONUNBUFFERED=${PYTHONUNBUFFERED:-})"

# Xvfb 虚拟显示（ODA File Converter 是 Qt GUI，需要 DISPLAY）
# 不使用 xvfb-run：slim 镜像缺少 xdpyinfo，会导致其就绪检测死等
export DISPLAY=:99
Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp &
sleep 1

exec python -u -m uvicorn masc_ahu_dwg2excel_api.api:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --log-level info \
  --access-log
