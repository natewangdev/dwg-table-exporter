# masc-ahu-dwg2excel-api
FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# ODA File Converter: download official Linux .deb at build time (use --build-arg to override)
ARG ODA_DEB_URL="https://www.opendesign.com/guestfiles/get?filename=ODAFileConverter_QT6_lnxX64_8.3dll_27.1.deb"
# Must match the /usr/bin/ODAFileConverter_<version> directory created by the .deb
ARG ODA_BUNDLE_SUBDIR=ODAFileConverter_27.1.0.0

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        wget \
        xvfb \
        xauth \
        libx11-6 \
        libxext6 \
        libxrender1 \
        libxi6 \
        libxtst6 \
        libgl1 \
        libglib2.0-0 \
        libxkbcommon0 \
        libfontconfig1 \
        libfreetype6 \
        libdbus-1-3 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-xinerama0 \
        libxcb-xkb1 \
        libxkbcommon-x11-0 \
        libsm6 \
        libice6 \
    ; \
    wget -qO /tmp/odafileconverter.deb "${ODA_DEB_URL}"; \
    apt-get install -y --no-install-recommends /tmp/odafileconverter.deb; \
    rm -f /tmp/odafileconverter.deb; \
    ldconfig; \
    if [ -f /usr/lib/x86_64-linux-gnu/libxcb-util.so.1 ] && [ ! -e /usr/lib/x86_64-linux-gnu/libxcb-util.so.0 ]; then \
        ln -sf libxcb-util.so.1 /usr/lib/x86_64-linux-gnu/libxcb-util.so.0; \
    fi; \
    rm -rf /var/lib/apt/lists/*

# Paths matching the official .deb layout under /usr/bin
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

EXPOSE 80
ENTRYPOINT ["/app/docker-entrypoint.sh"]
