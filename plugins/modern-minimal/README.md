# Modern Minimal（现代简约主题）

`plugins/modern-minimal/` 是一个**主题型插件**（`metadata.json` 的 `category` 为 `theme`
），面向个人博客与作品集：极简排版、响应式、自动深色模式，并支持代码高亮与目录导航。`plugin.py` 继承
`shared.services.plugins.plugin_manager.theme_plugin.ThemePlugin`。

## 文件

| 文件                                         | 作用                    |
|--------------------------------------------|-----------------------|
| `metadata.json`                            | 主题元数据 + 后台设置表单 schema |
| `plugin.py`                                | `ThemePlugin` 实现      |
| `theme.json`                               | 运行时配置（颜色、布局、排版）       |
| `theme.config.js`                          | 前端构建配置                |
| `styles.css`                               | 自定义样式                 |
| `screenshot.svg`                           | 后台预览图                 |
| `frontend/api.ts`、`frontend/manifest.json` | 前端扩展与插件清单             |

## 元数据

- `slug`: `modern-minimal`，`version`: `2.0.0`，`license`: MIT，`category`: `theme`
- `requires.fastblog`: `>=1.0.0`
- `tags`: `minimal`、`modern`、`clean`、`responsive`、`technology`、`code`、`dark-mode`
- `supports`: `custom-logo`、`custom-header`、`featured-image`、`post-thumbnails`、`comments`、`widgets`、`table-of-contents`、
  `code-highlighting`、`dark-mode`、`responsive-design`

## 可配置项（`settings_schema`）

与 `fastblog-default` 同构，按分组渲染在后台「扩展 → 主题」的设置表单里：`colors`（主色、次要色、强调色等）、`layout`、
`typography` 等，默认值见 `metadata.json`；也可直接编辑 `theme.config.js`。

## 使用

由插件系统加载与激活（`shared/services/plugins/plugin_manager/`），在后台切换。与其它主题共存时 `plugin_id` 必须互不相同。

## 许可

MIT License。
