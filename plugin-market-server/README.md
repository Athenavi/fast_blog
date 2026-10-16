# FastBlog 插件市场服务端（可自建）

给 FastBlog 实例用的**只读插件市场**：你把它部署到自己的域名/内网，
FastBlog 就能浏览、下载插件包并检查更新 —— 不再依赖任何官方托管服务。

同一份契约（[`API.md`](./API.md)）有两个实现，行为逐条对齐，按需选一个：

| 版本      | 目录              | 形态               | 依赖                                  |
|---------|-----------------|------------------|-------------------------------------|
| **Go**  | [`go/`](./go)   | 单二进制（编译后丢到服务器即可） | 无（纯标准库）                             |
| **PHP** | [`php/`](./php) | 单入口 + `src/` 类库  | PHP ≥ 8.1（`ext-zip`、`ext-mbstring`） |

两版都提供：目录/搜索/详情/版本/下载/分类/推荐/更新检查/健康检查，外加一个**极简浏览页**
（无任何外部资源，方便你部署完立刻自检"包放对没、能不能下载"）。

---

## 1. 数据布局（两版一致）

服务端只读插件包目录，**插件包由你自己放入**：

```
data/
├── config.json            # 可选：配置文件（两版通用，键名与下方配置项一致）
├── .cache/                # 服务端自己生成（sha256 缓存、限流计数），可随时删
└── plugins/
    ├── seo/
    │   ├── 1.0.0.zip      # 文件名必须是 {版本}.zip
    │   └── 1.2.0.zip
    └── shop/
        └── 2.1.0.zip
```

规则（服务端启动/刷新索引时会校验，不合规的包**跳过并在 `/health` 的 `warnings` 里列出**）：

- 目录名 = 插件 `slug`，必须匹配 `^[a-z0-9-]+$`
- 文件名 = 版本号，必须匹配 `^\d+\.\d+\.\d+$`
- ZIP 内根目录（或一级子目录）必须有 `metadata.json`，且其中 `slug` / `version` 必须与目录/文件名一致
- 包内还可放 `README.md`（详情页返回）、`CHANGELOG.md`、`plugin.py`、`frontend/`、`screenshots/`

`metadata.json` 最小示例（完整字段规范见 [`API.md` §5](./API.md)）：

```json
{
    "name": "SEO Auto",
    "slug": "seo",
    "version": "1.0.0",
    "description": "文章级 SEO 元数据",
    "author": "FastBlog Team",
    "category": "seo",
    "tags": [
        "seo",
        "meta"
    ],
    "requires": {
        "fastblog": ">=1.0.0"
    },
    "license": "MIT"
}
```

打包（与 FastBlog 的 `PluginInstaller.install_from_zip` 兼容）：

```bash
cd plugins/seo && zip -r ../../seo-1.0.0.zip . && cd ../..
mv seo-1.0.0.zip /path/to/plugin-market-server/data/plugins/seo/1.0.0.zip
```

---

## 2. 配置（两版完全一致）

优先级：**环境变量 > `config.json` / `config.php` > 内置默认值**。

| 配置项（JSON 键）          | 环境变量                | 默认                       | 说明                                |
|----------------------|---------------------|--------------------------|-----------------------------------|
| `listen`             | `PMS_LISTEN`        | `:8080`                  | 监听地址（Go 版 / PHP 内置服务器）            |
| `data_dir`           | `PMS_DATA_DIR`      | `./data`                 | 数据目录                              |
| `site_name`          | `PMS_SITE_NAME`     | `FastBlog Plugin Market` | 站点名                               |
| `readonly`           | `PMS_READONLY`      | `true`                   | 只读市场；`false` 才允许写（当前两版均未实现写接口，见下） |
| `admin_token`        | `PMS_ADMIN_TOKEN`   | 空                        | `readonly=false` 时必填，否则拒绝启动       |
| `upstream_url`       | `PMS_UPSTREAM_URL`  | 空                        | 预留：上游镜像                           |
| `rate_limit_per_min` | `PMS_RATE_LIMIT`    | `60`                     | 每 IP 每分钟请求上限，`0` = 关闭             |
| `index_ttl_seconds`  | `PMS_INDEX_TTL`     | `60`                     | 索引缓存秒数                            |
| `sign_download`      | `PMS_SIGN_DOWNLOAD` | `false`                  | 预留：下载签名（需 `admin_token` 作密钥）      |
| `max_upload_bytes`   | `PMS_MAX_UPLOAD`    | `33554432`               | 预留：上传上限                           |

> **当前实现是只读的**：任何对 `/api/**` 的非 `GET/HEAD` 请求都返回 `403 / 40300`。
> 发布插件的方式就是把 zip 放进 `data/plugins/{slug}/`（`index_ttl_seconds` 后自动生效）。

---

## 3. 运行

### 3.1 Go 版

```bash
cd go
go build -o plugin-market-server .          # 产出单个可执行文件，无外部依赖

PMS_DATA_DIR=/srv/plugin-market/data \
PMS_LISTEN=127.0.0.1:8080 \
./plugin-market-server
```

Docker（多阶段构建，最终镜像只有二进制）：

```dockerfile
FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go/ ./go/
RUN cd go && CGO_ENABLED=0 go build -o /out/pms .

FROM alpine:3.20
COPY --from=build /out/pms /usr/local/bin/pms
ENV PMS_DATA_DIR=/data PMS_LISTEN=:8080
VOLUME /data
EXPOSE 8080
ENTRYPOINT ["pms"]
```

### 3.2 PHP 版

```bash
cd php
cp config.example.php config.php     # 可选：改 data_dir / site_name 等

# 开发 / 小站：内置服务器
PMS_DATA_DIR=/srv/plugin-market/data php -S 0.0.0.0:8080 public/index.php
```

Nginx + PHP-FPM（生产）：

```nginx
server {
    listen 80;
    server_name plugins.example.com;
    root /srv/plugin-market-server/php/public;

    location / {
        try_files $uri /index.php$is_args$args;
    }
    location ~ \.php$ {
        include fastcgi_params;
        fastcgi_pass unix:/run/php/php8.2-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        # 只读市场：把写方法挡在入口之外（双保险）
        if ($request_method !~ ^(GET|HEAD)$) { return 403; }
    }
}
```

> 提示：PHP 版的限流用文件计数实现（FPM 无跨请求内存），生产建议同时在 nginx 上限流。

---

## 4. 与 FastBlog 对接

1. **部署本服务并确认可达**：

   ```bash
   curl -s http://127.0.0.1:8080/api/v1/health
   # {"code":0,"data":{"status":"ok","plugins":2,"warnings":[],...}}
   ```

2. **告诉 FastBlog 市场地址**：设置环境变量 `PLUGIN_MARKETPLACE_URL=http://你的市场地址/api/v1`
   （FastBlog 侧把原先硬编码的 `plugins.fastblog.com` 改为读该变量；留空 = 不启用远程市场）。

3. **安装流程不变**：FastBlog 下载 zip 后先校验响应头 `X-Checksum-Sha256`，
   再交给既有 `PluginInstaller.install_from_zip()`（依赖检查 → 版本兼容 → 落地 `plugins/{slug}/`）。

4. **检查更新**：`GET /api/v1/updates?slug=seo:1.0.0&slug=shop:2.1.0`
   只返回"有更新"的插件（含 `latest`、`download_url`、`sha256`）。

---

## 5. 自检清单

```bash
# Go 版
cd go && go vet ./... && go test ./...

# PHP 版（需 PHP ≥ 8.1）
cd php && php tests/smoke.php

# 端到端（服务已启动）
curl -s localhost:8080/api/v1/plugins | head -c 300
curl -sI localhost:8080/api/v1/plugins/seo/download/1.0.0     # 应有 X-Checksum-Sha256 与 application/zip
curl -s -X POST localhost:8080/api/v1/plugins                  # 应 403/40300（只读）
curl -s localhost:8080/api/v1/plugins/..%2f..%2fetc           # 应 400/40000（路径穿越被拒）
```

---

## 6. 安全设计要点

- 所有由 `slug` / `version` 拼出的路径都先过正则白名单（`Safe` 模块），不合法直接 400。
- ZIP 解析只读 `metadata.json` / `README.md` / `CHANGELOG.md`，单成员读取上限 4MB；包内 `slug`/`version`
  必须与目录/文件名一致（防"挂羊头卖狗肉"）。
- 只读模式拒绝一切写方法；`readonly=false` 且未配 `admin_token` 时**拒绝启动**（不裸奔）。
- Token 比较用常量时间实现（Go: `subtle.ConstantTimeCompare`；PHP: `hash_equals`）。
- 错误响应不含堆栈与磁盘路径；下载响应带 `X-Content-Type-Options: nosniff`。
- 内置按 IP 限流；索引告警通过 `/api/v1/health` 暴露，便于发现放错的包。
