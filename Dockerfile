FROM python:3.10-slim

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

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Linux ODA File Converter：构建前将文件放入 docker/oda/（见 docker/oda/README.md、README Docker 章节）
# 官方 .deb 安装后为 /usr/bin/ODAFileConverter + /usr/bin/ODAFileConverter_<版本>/ 整目录，请按相同结构拷入 docker/oda/。
COPY docker/oda /opt/oda

# 相对于 /opt/oda 的可执行文件路径（默认对应 Debian/Ubuntu 官方 deb 布局）
ARG ODA_BINARY=usr/bin/ODAFileConverter
# 与可执行文件同级的版本目录（内含 lib/、plugins/、qt.conf 等；版本号与主机安装一致时可改 build-arg）
ARG ODA_BUNDLE=usr/bin/ODAFileConverter_27.1.0.0

ENV ODAFC_EXEC_PATH=/opt/oda/${ODA_BINARY}
ENV LD_LIBRARY_PATH=/opt/oda/${ODA_BUNDLE}/lib:/opt/oda/${ODA_BUNDLE}:${LD_LIBRARY_PATH}
ENV QT_PLUGIN_PATH=/opt/oda/${ODA_BUNDLE}/plugins

RUN chmod +x "${ODAFC_EXEC_PATH}" \
    && test -x "${ODAFC_EXEC_PATH}" || ( \
        echo "ERROR: 未找到或未授权执行 ODA 程序: ${ODAFC_EXEC_PATH}" \
        && echo "请先将 Linux 版 ODA File Converter 按 README 拷入 docker/oda/，参见 docker/oda/README.md" \
        && exit 1 \
    ) \
    && test -d "/opt/oda/${ODA_BUNDLE}" || ( \
        echo "ERROR: 未找到 ODA 程序目录: /opt/oda/${ODA_BUNDLE}" \
        && echo "请拷入完整的 ODAFileConverter_<版本>/ 目录，或通过 --build-arg ODA_BUNDLE=... 指定路径" \
        && exit 1 \
    )

COPY . /app
# 避免应用目录内重复一份 ODA，减小镜像体积
RUN rm -rf /app/docker/oda

RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
