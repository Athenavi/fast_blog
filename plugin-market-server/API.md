# FastBlog 插件市场服务端 — 接口契约（v1）

> 本文件是 `plugin-market-server/` 的实现依据，也是 FastBlog 实例对接的规范。
> 契约先行：服务端实现（Go 或 PHP）与 FastBlog 侧客户端都必须遵守本文件。

## 1. 背景与目的

FastBlog 当前只有**本机插件目录扫描**：

- `shared/services/plugins/plugin_manager/marketplace.py` 的 `PluginMarketService` 只遍历
  `plugins/*/metadata.json`；构造时写的 `self.marketplace_url = "https://plugins.fastblog.com/api/v1"`
  **从未被任何代码请求**（该域名至今无法解析）。
- 也就是说"远程插件市场"是双缺口：客户端没实现 + 服务端不存在。

本项目提供一个**可自建的插件市场服务端**：任何站长都能把它部署到自己的域名，
再把 FastBlog 的 `marketplace_url` 指向自己的实例即可浏览 / 下载 / 检查更新插件。

## 2. 术语与对象

| 名称       | 含义                                                      |
|----------|---------------------------------------------------------|
| plugin   | 一个插件，由 `slug` 唯一标识（`^[a-z0-9-]+$`）                      |
| version  | 语义化版本 `^\d+\.\d+\.\d+$`（与 `PluginManifest.version` 同规则） |
| package  | 插件分发包，**ZIP**，解压后根目录或一级子目录含 `metadata.json`             |
| manifest | `metadata.json`，字段规范见 §5                                |

## 3. 端点契约（基础路径 `/api/v1`）

所有响应统一为 JSON；成功 `200`，错误见 §6。

### 3.1 列表 / 搜索

```
GET /api/v1/plugins?keyword=&category=&sort=name|rating|installs|updated&order=asc|desc&page=1&page_size=20
```

```json
{
    "code": 0,
    "data": {
        "items": [
            {
                "slug": "seo",
                "name": "SEO Auto",
                "version": "1.0.0",
                "summary": "…",
                "category": "seo",
                "author": "FastBlog Team",
                "icon": "🔍",
                "rating": 4.8,
                "installs": 1234,
                "updated_at": "2026-10-12T10:00:00Z",
                "download_url": "https://…/api/v1/plugins/seo/download/1.0.0",
                "tags": [
                    "seo",
                    "meta"
                ]
            }
        ],
        "total": 42,
        "page": 1,
        "page_size": 20
    }
}
```

> 字段名与前端已有约定对齐：`slug/name/version/description/author/category/icon/tags/rating/installs`。

### 3.2 详情

```
GET /api/v1/plugins/{slug}
```

在列表字段基础上追加：`readme`（Markdown 原文）、`changelog`、`license`、
`requires`（`{"fastblog": ">=1.0.0"}`）、`dependencies`（数组）、`capabilities`（数组）、
`screenshots`（URL 数组）、`versions`（可用版本列表，倒序）。

### 3.3 版本列表

```
GET /api/v1/plugins/{slug}/versions
→ { "code": 0, "data": { "slug": "seo", "latest": "1.2.0",
      "versions": [ { "version": "1.2.0", "published_at": "…", "changelog": "…",
                      "download_url": "…", "sha256": "…", "size": 20480 } ] } }
```

### 3.4 下载包

```
GET /api/v1/plugins/{slug}/download/{version}   → 200 application/zip
```

必须返回以下响应头，供客户端做完整性校验：

| Header                                                             | 说明                                |
|--------------------------------------------------------------------|-----------------------------------|
| `Content-Type: application/zip`                                    |                                   |
| `Content-Length`                                                   | 字节数                               |
| `X-Checksum-Sha256`                                                | 包的 sha256（客户端应与 `metadata` 中的值比对） |
| `Content-Disposition: attachment; filename="{slug}-{version}.zip"` |                                   |

### 3.5 分类 / 推荐 / 更新检查

```
GET /api/v1/categories                 → [{ "slug": "seo", "name": "SEO优化", "count": 3 }]
GET /api/v1/featured?limit=6           → 与列表 items 同构
GET /api/v1/updates?slug=seo:1.0.0&slug=shop:2.1.0
     → { "code": 0, "data": { "updates": [
           { "slug": "seo", "current": "1.0.0", "latest": "1.2.0",
             "download_url": "…", "changelog": "…" } ] } }
GET /api/v1/health                     → { "status": "ok", "version": "1.0.0", "plugins": 42 }
```

### 3.6 发布（可选，需 Token）

若启用"上传/发布"能力（见 §4），追加：

```
POST /api/v1/plugins                     上传新插件包（multipart，字段 file）→ 解析 metadata.json 入库
POST /api/v1/plugins/{slug}/versions     发布新版本（multipart）
DELETE /api/v1/plugins/{slug}            下架（软删除）
```

## 4. 可自定义配置（服务端）

服务端必须允许站长通过**配置文件 + 环境变量**自定义（优先级：环境变量 > 配置文件 > 默认值）：

| 配置项      | 环境变量                | 默认                       | 说明                                         |
|----------|---------------------|--------------------------|--------------------------------------------|
| 监听地址     | `PMS_LISTEN`        | `:8080`                  |                                            |
| 数据目录     | `PMS_DATA_DIR`      | `./data`                 | 存放插件包与索引                                   |
| 站点名      | `PMS_SITE_NAME`     | `FastBlog Plugin Market` | 出现在 `/health` 与首页                          |
| 是否只读     | `PMS_READONLY`      | `true`                   | `false` 才暴露 §3.6                           |
| 发布 Token | `PMS_ADMIN_TOKEN`   | 空                        | 为空且 `PMS_READONLY=false` 时**必须拒绝启动**（避免裸奔） |
| 上游镜像     | `PMS_UPSTREAM_URL`  | 空                        | 非空时作为"镜像站点"代理上游目录                          |
| 全局限流     | `PMS_RATE_LIMIT`    | `60/min`                 | 按 IP                                       |
| 是否开启下载签名 | `PMS_SIGN_DOWNLOAD` | `false`                  | 开启后下载 URL 带 `expires`+`sig`                |
| 索引缓存秒数   | `PMS_INDEX_TTL`     | `60`                     |                                            |

配置文件示例（`config.yaml` / `config.json`；PHP 版可直接用 `config.php` 返回数组）见实现目录。

## 5. `metadata.json` 字段规范（与 `PluginManifest` 对齐）

**必需**：`name`、`slug`（`^[a-z0-9-]+$`）、`version`（`^\d+\.\d+\.\d+$`）

**可选**：`description`(≤500)、`author`、`author_url`、`author_email`、`plugin_url`、
`documentation_url`、`icon`、`category`、`license`(默认 MIT)、`tags`、`requires`
（如 `{"fastblog": ">=1.0.0", "python": ">=3.8"}`）、`dependencies`、
`plugin_dependencies`、`capabilities`（`resource:action` 形式）、`hooks`、
`settings_schema`、`changelog`、`screenshots`

服务端**必须**在入库时校验：slug 与 version 的正则、必需字段存在、ZIP 内
`metadata.json` 的 `slug` 与请求路径一致；并计算并存储包的 `sha256` 与 `size`。

> 真实样例见 `plugins/seo/metadata.json` 与 `plugins/approval/frontend/manifest.json`。

## 6. 错误响应

```json
{
    "code": 40401,
    "message": "plugin not found: foo",
    "data": null
}
```

| HTTP | code  | 场景                              |
|------|-------|---------------------------------|
| 400  | 40000 | 参数非法（slug/version 格式、分页越界）      |
| 401  | 40100 | 需要 Token 或 Token 无效             |
| 403  | 40300 | 只读模式下的写操作、签名校验失败                |
| 404  | 40401 | 插件 / 版本 / 包文件不存在                |
| 409  | 40900 | 同 slug+version 已存在              |
| 413  | 41300 | 上传包超过 `PMS_MAX_UPLOAD`（默认 32MB） |
| 429  | 42900 | 触发限流                            |
| 500  | 50000 | 服务端错误（**不得回显堆栈或文件路径**）          |

## 7. 与 FastBlog 的对接点

1. **配置**：FastBlog 侧新增环境变量 `PLUGIN_MARKETPLACE_URL`（默认留空 = 关闭远程市场），
   替换 `marketplace.py` 中硬编码的 `https://plugins.fastblog.com/api/v1`。
2. **客户端**（待实现，属 P0 的"修死链"收口）：
   `GET /api/v3/extension/plugin/market`（`plugin:view` 权限）代理服务端的 §3.1/§3.2，
   并在服务端不可达时**如实返回"远程市场未配置/不可达"**，而不是返回空列表冒充成功。
3. **安装**：复用既有 `PluginInstaller.install_from_zip()`（ZIP → `metadata.json` → 依赖检查 →
   版本兼容检查 → 落地 `plugins/{slug}/`）；下载后的包必须先校验 `X-Checksum-Sha256`。

## 8. 安全要求（服务端）

- 目录穿越：所有以 slug/version 拼接的路径必须先做白名单校验（`^[a-z0-9-]+$` / `^\d+\.\d+\.\d+$`）。
- ZIP 处理：拒绝含绝对路径 / `..` / 符号链接成员的包（与客户端 `install_from_zip` 的检查一致）。
- 写接口：`PMS_READONLY=false` 时必须配置 `PMS_ADMIN_TOKEN`，Token 用常量时间比较。
- 不记录 Token 与请求体到日志；错误响应不回显堆栈。
- 上传大小上限、下载限流、可选签名（`PMS_SIGN_DOWNLOAD`）。
