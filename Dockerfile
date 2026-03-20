# masc-ahu-dwg2excel-api
FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# ODA File Converter：构建时下载官方 Linux .deb（版本或 URL 变更时使用 --build-arg）
ARG ODA_DEB_URL="https://www.opendesign.com/guestfiles/get?filename=ODAFileConverter_QT6_lnxX64_8.3dll_27.1.deb"
# 与 .deb 安装后的 /usr/bin/ODAFileConverter_<版本> 目录名一致（随 ODA 版本调整）
ARG ODA_BUNDLE_SUBDIR=ODAFileConverter_27.1.0.0

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        wget \
        xvfb \
        libx11-6 \
        libxext6 \
        libxrender1 \
        libxi6 \
        libxtst6 \
        libgl1 \
        libglib2.0-0 \
    ; \
    wget -qO /tmp/odafileconverter.deb "${ODA_DEB_URL}"; \
    apt-get install -y --no-install-recommends /tmp/odafileconverter.deb; \
    rm -f /tmp/odafileconverter.deb; \
    ldconfig; \
    if [ -f /usr/lib/x86_64-linux-gnu/libxcb-util.so.1 ] && [ ! -e /usr/lib/x86_64-linux-gnu/libxcb-util.so.0 ]; then \
        ln -sf libxcb-util.so.1 /usr/lib/x86_64-linux-gnu/libxcb-util.so.0; \
    fi; \
    rm -rf /var/lib/apt/lists/*

# 安装路径与官方 .deb 一致（在 /usr/bin 下）
ENV ODAFC_EXEC_PATH=/usr/bin/ODAFileConverter \
    ODA_BUNDLE_PATH=/usr/bin/${ODA_BUNDLE_SUBDIR} \
    LD_LIBRARY_PATH=/usr/bin/${ODA_BUNDLE_SUBDIR}/lib:/usr/bin/${ODA_BUNDLE_SUBDIR}:${LD_LIBRARY_PATH} \
    QT_PLUGIN_PATH=/usr/bin/${ODA_BUNDLE_SUBDIR}/plugins

RUN set -eux; \
    test -x "${ODAFC_EXEC_PATH}"; \
    test -d "${ODA_BUNDLE_PATH}"

COPY pyproject.toml requirements.txt /app/
COPY src /app/src
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir .

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
