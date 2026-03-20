# masc-ahu-dwg2excel-api
FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxi6 \
    libxtst6 \
    libgl1 \
    libglib2.0-0 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 先安装依赖与可编辑包（不把 docker/oda 大文件打进依赖层）
COPY pyproject.toml requirements.txt /app/
COPY src /app/src
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir .

# Linux ODA File Converter：构建前将文件放入 docker/oda/
COPY docker/oda /opt/oda

ARG ODA_BINARY=usr/bin/ODAFileConverter
ARG ODA_BUNDLE=usr/bin/ODAFileConverter_27.1.0.0

ENV ODAFC_EXEC_PATH=/opt/oda/${ODA_BINARY}
ENV LD_LIBRARY_PATH=/opt/oda/${ODA_BUNDLE}/lib:/opt/oda/${ODA_BUNDLE}:${LD_LIBRARY_PATH}
ENV QT_PLUGIN_PATH=/opt/oda/${ODA_BUNDLE}/plugins

RUN chmod +x "${ODAFC_EXEC_PATH}" \
    && test -x "${ODAFC_EXEC_PATH}" || ( \
        echo "ERROR: 未找到或未授权执行 ODA 程序: ${ODAFC_EXEC_PATH}" \
        && echo "请先将 Linux 版 ODA File Converter 拷入 docker/oda/，参见 docker/oda/README.md" \
        && exit 1 \
    ) \
    && test -d "/opt/oda/${ODA_BUNDLE}" || ( \
        echo "ERROR: 未找到 ODA 程序目录: /opt/oda/${ODA_BUNDLE}" \
        && echo "请拷入完整的 ODAFileConverter_<版本>/ 目录，或通过 --build-arg ODA_BUNDLE=... 指定路径" \
        && exit 1 \
    )

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
