# 无障碍模块交付报告（`/system/accessibility`）

范围：仅新建 `frontend/web/.gen/accessibility/`，未改动仓库任何其它文件。
契约来源：`src/api/v3/modules/system/accessibility/controller.py`（+ `schema.py` + `service.py` 全量核对）。
HTTP 前缀：`request.ts` 的 `baseURL = /api/v3`，故下列路径均省略 `/api/v3` 前缀。

## 1. 后端 8 端点 → 前端 API 函数 → 页面承载位置

| # | 后端端点（方法 路径）                            | 权限                            | 前端 API 函数                                     | 页面承载位置                                          |
|---|----------------------------------------|-------------------------------|-----------------------------------------------|-------------------------------------------------|
| 1 | `GET /system/accessibility/config`     | 公开                            | `accessibilityApi.getConfig()`                | 配置 Tab · 初始化加载配置表单                              |
| 2 | `PUT /system/accessibility/config`     | `module_system:setting:edit`  | `accessibilityApi.saveConfig(data)`           | 配置 Tab · 「保存配置」按钮（顶部 actions，`v-auth`）          |
| 3 | `GET /system/accessibility/css`        | 公开                            | `accessibilityApi.getCss()`                   | 配置 Tab · 「生成的样式表」预览块（保存后自动刷新 + 「重新生成」）          |
| 4 | `GET /system/accessibility/skip-links` | 公开                            | `accessibilityApi.skipLinks()`                | 指南与工具 Tab · 「跳过链接」表格                            |
| 5 | `GET /system/accessibility/shortcuts`  | 公开                            | `accessibilityApi.shortcuts()`                | 指南与工具 Tab · 「键盘快捷键」表格                           |
| 6 | `POST /system/accessibility/aria`      | 公开                            | `accessibilityApi.aria(elementType, context)` | 指南与工具 Tab · 「ARIA 建议」工具（选元素类型 + 可选标签 → 属性表）     |
| 7 | `POST /system/accessibility/validate`  | `module_content:article:edit` | `accessibilityApi.validate(html)`             | HTML 校验 Tab · 粘贴 HTML → 评分 / 级别 / 规则表（`v-auth`） |
| 8 | `GET /system/accessibility/guide`      | 公开                            | `accessibilityApi.guide()`                    | 指南与工具 Tab · 标准说明 + 特性卡片                         |

**8 / 8 端点全部接线，无未接线端点。**

## 2. 未接线的端点 / 能力及原因

无。全部 8 个端点均有页面承载。以下为**刻意保留的边界**（非占位、非假数据）：

- **ARIA 工具只暴露 `context.label`**：后端 `aria_labels()` 中仅 `navigation` / `search` 使用 `context.label`，
  `form` 使用 `context.labelledby`，其余类型忽略 `context`。页面只提供一个「标签」输入（用于 navigation / search），
  **未伪造** labelledby 输入或对无效类型编造属性 —— 选其它类型时后端返回其固定属性集。
- **配置提交全部已知键**：`saveConfig` 提交表单里 7 个已知键（均属后端 `DEFAULT_CONFIG`）。后端收原始 dict 并对
  未知键 / 非法字号返回 400；前端不产生未知键，故不会触发该拒绝路径（错误仍由 request 拦截器统一提示）。

## 3. 后端契约逐条核对

- **请求体字段**：`PUT config` 收原始 dict，键 = `DEFAULT_CONFIG`（`keyboard_navigation` / `screen_reader_support` /
  `high_contrast_mode` / `font_size` / `reduce_motion` / `focus_visible` / `skip_links`）——与 `AccessibilityConfig` 一致。
  `POST aria` = `{element_type, context}`；`POST validate` = `{html}`。均与 `schema.py` 对齐。
- **响应形状**：`css` → `{config, css}`；`skip-links` / `shortcuts` → 数组；`aria` → `{element_type, attributes}`；
  `validate` → `{valid, score, errors[], warnings[], infos[], summary{errors,warnings,infos,elements_checked}}`；
  `guide` → `{standard, features[], shortcuts[], skip_links[]}`。类型定义与之逐字段一致。
- **权限码**（反查 `src/api/v3/core/permission/codes.py`）：
    - 页面 `permission: 'module_system:setting:view'`（`codes.SETTING_VIEW`）；
    - 保存按钮 `v-auth="'module_system:setting:edit'"`（`codes.SETTING_EDIT`）；
    - 校验按钮 `v-auth="'module_content:article:edit'"`（`codes.ARTICLE_EDIT`）。
- **字号枚举**：`small / medium / large / x-large`（对齐 `FONT_SIZE_PX`）。

## 4. 遵循的既有范式

- API 客户端：`import http from '../request'`；`http.get/put/post`；导出 `accessibilityApi` 对象 + interface 类型
  （参照 `src/api/modules/points.ts`、`monitoring.ts`）。
- 页面：`AdminPage` 壳 + `el-tabs` 多页签（参照 `src/pages/system/integrations.vue`、`monitoring.vue`）；
  `definePageMeta({layout:'admin', middleware:'auth', title, permission})`；`@/api` 聚合导入；
  `@/utils/feedback` 的 `ElMessage`；`v-auth` 指令；文案全部走 `t('admin.system.accessibility.…')` / `$t(...)`。
- 只读加载用 `Promise.allSettled`，失败不产生未处理拒绝（错误由 request 拦截器统一提示）。
- 本页为配置页（无分页列表），未使用 `useAdminList`（与 `setting.vue` 的表单模式同理）。

## 5. 产物文件清单

```
frontend/web/.gen/accessibility/api/accessibility.ts     API 客户端模块（8 个函数 + 全部 interface）
frontend/web/.gen/accessibility/pages/accessibility.vue  页面（配置 / HTML 校验 / 指南与工具 三页签）
frontend/web/.gen/accessibility/i18n.json                双语键（admin.system.accessibility.*，含 admin 根）
frontend/web/.gen/accessibility/REPORT.md                本报告
```

均为 UTF-8 + LF。

## 6. 存疑之处

1. **页面主权限码**：后端 accessibility 模块**没有独立的 view 权限码**（config 读公开、写 `setting:edit`、
   validate `article:edit`）。本页选 `module_system:setting:view`（其本质是系统设置类页面）。若父代理在
   `menus.ts` / 路由收口时约定别的权限码，请以父代理为准统一替换（页面内仅此一处）。
2. **`skip_links` 命名冲突**：后端配置键与「跳过链接列表」端点同名 `skip_links`；页面中前者是配置开关
   （`AccessibilityConfig.skip_links`），后者是 `accessibilityApi.skipLinks()` 返回的链接数组，两者含义不同、互不影响。
3. **无法运行验证**：按铁律未执行任何 shell 命令（未跑 npm / nuxt / tsc / playwright / git），
   所有类型与路径均逐行对照后端源码与既有范式，未经编译或运行验证。
4. **i18n 合并方式**：`i18n.json` 采用 `{"zh-CN": {"admin": {...}}, "en": {"admin": {...}}}` 结构，
   假定父代理按 `admin.system.accessibility` 路径合并进 `i18n/locales/{zh-CN,en}.json`；若合并层级不同需相应调整。
