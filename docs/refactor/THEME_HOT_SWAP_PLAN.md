# 主题热插拔方案（L1 声明式区块 + L2 自带组件）

> 状态：**设计待裁决**。用户已选定方向为「A + C 的结合，以业界权威做法为准」。
> 更新时间：2026-10-16

---

## 1. 问题

当前主题的加载路径是**构建期**的：

```
plugins/<slug>/frontend/site/*.vue
   ↓ prescan 复制（构建期）
frontend/web/src/.plugin-pages/<slug>/site/*.vue
   ↓ import.meta.glob 收集（构建期）
_loader.ts → ThemePage 运行时按 slug 查表
```

结果：**换主题（DB 状态）是热的，主题代码本身是冷的** —— 新增或修改主题页面必须重新构建。
这与「插件 = 热插拔」的目标冲突。

**根因**：Vue SFC 需要编译（模板 → render 函数），浏览器里没有 SFC 编译器。
所以真热插拔**必须换一种主题表达形式**，或把编译下放到主题自身。

---

## 2. 方案：两层主题能力

业界成熟 CMS 都是这个形状：**声明式为主，需要逻辑时才带代码**。

| 参考             | 声明式层                          | 代码层      |
|----------------|-------------------------------|----------|
| WordPress 区块主题 | `theme.json` + 区块             | 插件带 PHP  |
| Shopify        | Liquid + Section/Block schema | App 扩展   |
| Halo           | 主题模板包（装上即用）                   | 插件（Java） |

对应到本项目：

### L1：声明式区块（覆盖绝大多数主题，零构建、上传即用）

主题在 `theme.json` 里**用区块描述页面**，前端内置**通用渲染器**解释执行。

```json
{
  "templates": {
    "HomePage": [
      {"block": "site-header", "props": {"showLogo": true}},
      {"block": "post-list", "props": {"limit": 6, "layout": "grid", "columns": 3}},
      {"block": "category-nav", "props": {"style": "tag"}},
      {"block": "site-footer"}
    ],
    "ArchivePage": [
      {"block": "page-title", "props": {"text": "文章"}},
      {"block": "post-list", "props": {"limit": 12, "layout": "list", "paginated": true}}
    ],
    "ArticlePage": [
      {"block": "post-header", "props": {"showSummary": true}},
      {"block": "post-content"},
      {"block": "post-tags"}
    ]
  }
}
```

- **后端**在 `GET /extension/theme/public/templates`（或并入现有 `public/config`）返回这份描述。
- **前端** `<ThemePage page="HomePage">` 改为：**先找 L2 组件，找不到就读 L1 区块列表并渲染**，都没有才回退内置页面。
- **热插拔**：改 `theme.json` → 刷新即生效，**零构建**。

**内置区块清单（首批，够拼出常见主题）**：

`site-header` / `site-footer` / `post-list`（参数：limit、layout=grid|list|compact、columns、paginated、category）
`post-header` / `post-content` / `post-tags` / `post-meta` / `post-card`
`page-title` / `category-nav` / `tag-cloud` / `search-box` / `pagination` / `html`（受净化的富文本）

**安全**：区块类型与参数都走**白名单**（未知区块 → 跳过并告警，而不是渲染未知内容）；
参数值复用主题变量那套校验（拒 `;{}/*<>`）。

### L2：主题自带的预构建组件（表现力完整）

需要自定义交互的主题，**自己构建**成一个 ESM bundle，随主题包分发。

```
plugins/<slug>/frontend/dist/theme.js     ← 主题自己打包的产物
plugins/<slug>/frontend/dist/manifest.json ← 入口与组件清单
```

- **后端**提供 `GET /extension/theme/public/bundle` 返回**当前主题的 bundle 地址**（或直接流式返回文件）。
- **前端**运行时 `await import(/* @vite-ignore */ url)` 加载，按 manifest 取组件。
- **热插拔**：上传主题 → 直接生效，**主站不重新构建**。
- **代价（必须诚实计入）**：
    - 主题需**独立构建**（不是"无构建"，只是与主站解耦）；
    - **版本兼容**：bundle 依赖的 Vue 运行时版本要与主站一致 → 约定 `vue` / `@vue/runtime-core` 走 **externals**，由主站提供；
    - **安全**：bundle 是**可执行代码** → 仅允许**管理员上传**，不接受第三方任意注册；可选加签名校验；
    - **跨源**：建议同源路径（`/plugin-assets/<slug>/theme.js`）而非外部 CDN，避免 CORS 与 CSP 复杂化。

---

## 3. 实施顺序（建议）

1. **L1 先做**（收益最大、风险最低）：区块协议 + 内置区块集 + 渲染器；三款内置主题的 `theme.json` 改写为区块描述，
   删掉 `frontend/site/*.vue`（或保留为 L2 示例）。
2. **前端回退链改造**：`ThemePage` 解析顺序 = L2 组件 → L1 区块 → 默认插槽。
3. **L2 后做**：bundle 约定 + 运行时加载 + externals 契约 + 管理员上传入口。
4. **prescan 退居次要**：L1/L2 都不再依赖 `src/.plugin-pages/`；该目录仅保留给**仍走编译期的插件后台页**
   （`frontend/admin/*.vue`），或者一并迁到 L2。

---

## 4. 需要先定的事（未决）

- [ ] **区块协议的具体字段**（`block` / `props` / 是否支持 `children` 嵌套、条件渲染 `when`）
- [ ] **L1 与 L2 的优先级**：同一页面两边都定义了怎么办（建议 L2 覆盖 L1，并在后台提示）
- [ ] **L2 bundle 的加载是否要签名/校验**（多租户下建议要）
- [ ] **内置区块清单的最终范围**（上面的首批是否够三款主题改写）
- [ ] **`theme.json` 的向后兼容**：现有 `componentSlots` / `settings_schema` 保留，仅新增 `templates`
- [ ] **三款主题的呈现是否要在 L1 下保持**（当前 `t-*` 类名与设计语言需由区块的 `props` 表达出来）
- [ ] **是否保留"构建期 Vue 页面"作为一种主题形态**（对内置官方主题仍是最省事的方式）

---

## 5. 与现状的关系

- **已完成的、不受影响的部分**：主题设置 → CSS 变量块（`theme/variables.py`）、配置存储、切换机制、
  CSS 注入顺序 —— 这些与"页面怎么来"无关，L1/L2 都复用。
- **会被替换的部分**：`composables/useThemePage.ts`（改为解析区块描述）、三款主题的 `frontend/site/*.vue`
  （改写为 `theme.json` 的 `templates`）、`scripts/scan-plugin-frontend.mjs` 对 `site/` 的复制（L1/L2 后不再必需）。
- **本轮已实现但因非热插拔而需迁移**：三款主题各 3 个页面组件（`HomePage` / `ArchivePage` / `ArticlePage`）。
