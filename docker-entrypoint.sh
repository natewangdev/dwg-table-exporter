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

exec xvfb-run -a uvicorn dwg_table_exporter.api:app --host 0.0.0.0 --port "${PORT:-8000}"
