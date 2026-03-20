# ODA File Converter（Linux）— 打包进 Docker 镜像

构建镜像前，请将 **Linux 版** ODA File Converter 的安装文件复制到本目录 `docker/oda/`（与 ODA 官方许可一致，本仓库不包含该二进制）。

## 推荐：与官方 `.deb` 相同的目录结构

在 Debian/Ubuntu 上通过 `apt`/`.deb` 安装后，文件通常在：

- `/usr/bin/ODAFileConverter`（启动入口）
- `/usr/bin/ODAFileConverter_<版本>/`（**整目录**：内含真实 `ODAFileConverter`、`lib/`、`plugins/`、`qt.conf` 等）

在项目仓库**根目录**执行，将上述内容拷入 `docker/oda`（保留 `usr/bin/...` 结构）：

```bash
mkdir -p docker/oda/usr/bin
cp -a /usr/bin/ODAFileConverter docker/oda/usr/bin/
cp -a /usr/bin/ODAFileConverter_27.1.0.0 docker/oda/usr/bin/
```

> 若你主机上的版本目录名不是 `ODAFileConverter_27.1.0.0`，以 `dpkg -L odafileconverter | grep ODAFileConverter_` 为准，并在构建镜像时用  
> `--build-arg ODA_BUNDLE=usr/bin/ODAFileConverter_<你的版本>`。

构建镜像：

```bash
docker build -t dwg-table-exporter:latest .
```

（`Dockerfile` 已默认 `ODA_BINARY=usr/bin/ODAFileConverter`、`ODA_BUNDLE=usr/bin/ODAFileConverter_27.1.0.0`，并设置 `LD_LIBRARY_PATH` / `QT_PLUGIN_PATH`。）

## 其他布局

若你把可执行文件直接放在 `docker/oda/ODAFileConverter` 且无独立 bundle 目录，可构建时指定：

```bash
docker build \
  --build-arg ODA_BINARY=ODAFileConverter \
  --build-arg ODA_BUNDLE=. \
  -t dwg-table-exporter:latest .
```

（需确保 `.so` 与 `plugins` 仍能被动态链接器/Qt 找到，否则优先采用官方 deb 的 `usr/bin` 布局。）

## 许可说明

ODA File Converter 受 Open Design Alliance 等许可约束，请自行取得合法安装包后再执行 `docker build`。
