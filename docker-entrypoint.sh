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

PORT="${PORT:-8000}"
# 立即输出一行，便于 docker logs 确认脚本已执行（避免误以为“无日志”）
echo "[entrypoint] Starting API on 0.0.0.0:${PORT} (PYTHONUNBUFFERED=${PYTHONUNBUFFERED:-})"

# python -u：无缓冲 stdout/stderr；--access-log：请求日志写入 Docker 日志
exec xvfb-run -a python -u -m uvicorn masc_ahu_dwg2excel_api.api:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --log-level info \
  --access-log
