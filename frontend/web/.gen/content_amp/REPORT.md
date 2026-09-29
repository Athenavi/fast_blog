# content/amp 前端接线报告

工作区：`X:\project\fast_blog`（Windows）。全部产物位于 `frontend/web/.gen/content_amp/`，
**未修改仓库中任何其它文件**。

## 一、端点 → 前端映射表

| 后端端点                                       | 方法   | 权限码（codes.py）                                 | 前端 `ampApi` 方法                      | 承载位置                                 |
|--------------------------------------------|------|-----------------------------------------------|-------------------------------------|--------------------------------------|
| `/api/v3/content/amp/article/{article_id}` | GET  | `module_content:article:view`（`ARTICLE_VIEW`） | `ampApi.articleDocument(articleId)` | `pages/seo.vue` → AMP 工具 → 「按文章生成」   |
| `/api/v3/content/amp/convert`              | POST | `module_content:article:edit`（`ARTICLE_EDIT`） | `ampApi.convert(payload)`           | `pages/seo.vue` → AMP 工具 → 「HTML 转换」 |
| `/api/v3/content/amp/validate`             | POST | `module_content:article:view`（`ARTICLE_VIEW`） | `ampApi.validate(payload)`          | `pages/seo.vue` → AMP 工具 → 「规范校验」    |

承载页选择：`frontend/web/src/pages/analytics/seo.vue`。理由：

1. AMP 是 SEO 交付物，后端 `service.generate_for_article` 的站点名/基址**直接复用**
   `analytics/seo` 的 `schema_org_service.site_context`，两者同源；
2. 该页已是多 tab 工具集合（综合报告 / 批量检查 / 关键词 / 孤立文章 / 内容分析器 / 跳转规则），
   追加一个 `name="amp"` 的 tab 与既有结构一致；
3. 页级权限 `module_analytics:seo:view` 覆盖入口，AMP 各操作按钮再用 `v-auth` 细化到
   `module_content:article:view` / `module_content:article:edit`。

页面形态：**逐字保留** `seo.vue` 原有 `<script>`/`<template>`/`<style>` 全部内容，仅：

- 顶部注释块追加一行 AMP 说明；
- icon import 追加 `CopyDocument`；
- `from '@/api'` 聚合 import 追加 `ampApi` 与 4 个类型；
- `<script>` 末尾追加「AMP 工具」逻辑段；
- 最后一个 `el-tab-pane` 之后、`</el-tabs>` 之前追加 AMP tab；
- `<style>` 末尾追加 `.mr-1` / `.ml-2` / `.amp-validation` 三条样式。

## 二、字段来源

### 请求体（`schema.py`）

- `AmpConvertRequest`：`html`(必填,1..500000) / `title`(≤255) / `author_name`(≤255) /
  `canonical_url`(≤500) / `site_name`(≤255) / `featured_image`(≤1000) /
  `published_at`(ISO,≤64) / `extra_css`(≤200000) → `AmpConvertPayload`。
- `AmpValidateRequest`：`html`(必填,1..500000) → `AmpValidatePayload`。
- 前端 `buildAmpConvertPayload()` 只提交有值的可选字段（空串不发送）。

### 响应体（`service.py`）

- `GET .../article/{id}` ← `AmpService.generate_for_article`：
  `article_id` / `title` / `slug` / `canonical_url` / `site`(=site_context) / `components` /
  `removed_tags` / `css`(`bytes`,`limit`,`truncated`) / `amp_html` / `validation` → `AmpArticleDocument`。
- `POST .../convert` ← `AmpService.convert_to_amp`：
  `amp_html` / `canonical_url` / `components` / `removed_tags` / `css` / `validation` → `AmpConvertResult`。
- `POST .../validate` ← `AmpService.validate_amp`：
  `valid` / `errors[]`(`rule`,`message`) / `warnings[]` / `summary`(`errors`,`warnings`,`css_bytes`,
  `css_limit`,`elements_checked`) → `AmpValidationResult`（`errors`/`warnings` 内嵌于 convert/article 的
  `validation` 字段，同构复用）。
- `site` ← `analytics/seo/schema_org.py::site_context`：`{name, base_url, logo, source}` → `AmpSiteContext`。

### i18n

新增键全部挂在 `admin.analytics.seo.*`（承载页调用路径），`i18n.json` 以 `{"zh-CN":…,"en":…}`
给出双语对称的**仅新增键**，共 52 键 ×2。

## 三、未接线及原因

- **无遗漏**：controller 中 3 个端点全部接线。
- `service.py` 的 `render_document` / `build_document` / `convert_html_fragment` / `limit_css` /
  `to_datetime` 为内部纯函数/便捷封装，无独立路由，不接线。
- `article/[id].vue`（文章编辑页）未改动：任务候选承载页，但编辑页聚焦正文编辑，
  不宜承载「任意 HTML 转换/校验」这类工具；且改编辑页风险更高。AMP 归入 SEO 工具更内聚。

## 四、存疑

1. **页级权限与操作权限不一致**：`seo.vue` 页级 `definePageMeta.permission` 为
   `module_analytics:seo:view`，而 AMP 生成/校验需 `module_content:article:view`、转换需
   `module_content:article:edit`。入口权限用的是 seo:view。已在每个操作按钮加 `v-auth` 细化，
   但「只有 article:view 而无 seo:view 的用户无法从该入口进入」这一组合未处理——若需独立入口，
   应新增路由/菜单项（本次未做，超出「追加工具区」范围）。
2. `navigator.clipboard.writeText` 依赖安全上下文（HTTPS/localhost）；非安全上下文会 reject，
   已 try/catch 并提示 `ampCopyFailed`，未做降级复制。
3. `site` 的 `logo`/`source` 在 UI 未展示（后端返回但页面未用到），仅类型保留。
4. `published_at` 前端按 ISO 字符串透传，未做格式校验；后端 `to_datetime` 解析失败会静默忽略。

## 五、未编译声明

**本子智能体无 shell 权限，未运行任何构建 / 类型检查（`vue-tsc` / `vite build` / eslint 均未执行）。**
以下为静态自查结论，非编译验证：

- 无 mock、无编造数据；字段与后端返回字典逐项对齐。
- 未使用 `as` 掩盖类型；页面内未引入未 import 的符号。
- 页面 API 通过 `from '@/api'` 聚合导入，**依赖下方的 re-export 块先合入 `src/api/index.ts`**，
  否则 `ampApi` 与相关类型不可解析（这是集成前提，非本产物缺陷）。
- 集成步骤（需在仓库其它文件上执行，本次未做）：
    1. 将 `api/amp.ts` 复制为 `frontend/web/src/api/modules/amp.ts`；
    2. 把 `pages/seo.vue` 覆盖 `frontend/web/src/pages/analytics/seo.vue`；
    3. 将下方 re-export 块并入 `frontend/web/src/api/index.ts`；
    4. 将 `i18n.json` 的 `zh-CN`/`en` 子树分别合并进 `i18n/locales/zh-CN.json`、`en.json`。

## 六、re-export 块

并入 `frontend/web/src/api/index.ts` 的 content 段（`articleApi` 附近）：

```ts
export {ampApi} from './modules/amp'
export type {
  AmpArticleDocument,
  AmpConvertPayload,
  AmpConvertResult,
  AmpCssInfo,
  AmpSiteContext,
  AmpValidatePayload,
  AmpValidationResult,
  AmpValidationSummary,
  AmpViolation,
} from './modules/amp'
```
