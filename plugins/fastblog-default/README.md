# FastBlog Default（默认主题）

`plugins/fastblog-default/` 是一个**主题型插件**：`metadata.json` 的 `category` 为 `theme`，`plugin.py` 继承
`shared.services.plugins.plugin_manager.theme_plugin.ThemePlugin`（`plugin_id=1001`），通过 EventBus 订阅事件来扩展站点外观。

## 文件

| 文件                       | 作用                                              |
|--------------------------|-------------------------------------------------|
| `metadata.json`          | 主题元数据 + 后台设置表单 schema                           |
| `plugin.py`              | `ThemePlugin` 实现（注册 EventBus 订阅）                |
| `theme.json`             | 运行时配置（颜色、布局、排版）                                 |
| `theme.config.js`        | 前端构建配置                                          |
| `styles.css`             | 自定义样式                                           |
| `screenshot.svg`         | 后台预览图                                           |
| `frontend/manifest.json` | 前端插件清单（供 `scripts/scan-plugin-frontend.mjs` 扫描） |

## 元数据

- `slug`: `fastblog-default`，`version`: `1.0.0`，`license`: MIT，`category`: `theme`
- `requires.fastblog`: `>=1.0.0`
- `supports`: `custom-logo`、`custom-header`、`featured-image`、`post-thumbnails`、`comments`、`widgets`

## 可配置项（`settings_schema`）

| 分组           | 字段                                                                                    | 默认值                                                       |
|--------------|---------------------------------------------------------------------------------------|-----------------------------------------------------------|
| `colors`     | `primary` / `secondary` / `accent` / `background` / `foreground`                      | `#3b82f6` / `#64748b` / `#f59e0b` / `#ffffff` / `#1f2937` |
| `layout`     | `sidebar_position`（left/right/none）、`content_width`（max-w-4xl/5xl/7xl）、`show_sidebar` | `right` / `max-w-4xl` / `true`                            |
| `typography` | `font_family`、`font_size`、`line_height`                                               | `Inter, system-ui, sans-serif` / `16px` / `1.6`           |

## 使用与派生

主题由插件系统加载与激活（`shared/services/plugins/plugin_manager/`），后台「扩展 → 主题」中切换与配置。派生新主题：复制本目录，改
`metadata.json`（`name`/`slug`/`version`/`screenshot`）与 `theme.config.js`，再让插件管理器重新扫描。

> 注意：`plugin.py` 的 `plugin_id` 需与其他主题不同，否则会与既有主题冲突。
