# 插件前端约定

`plugins/<name>/frontend/` 下的页面会在 `npm run prescan` 时被复制到
`frontend/web/src/.plugin-pages/<name>/`，由 `_loader.ts` 在后台挂载
（`.plugin-pages/` 是**生成目录，不要手改**——改这里的源文件）。

## 后台插件页面（`*/admin/Page.vue`）

后台运行在 Element Plus 语境里，UI 有两条硬约定（与 `frontend/web/README.md` 的「UI 边界」一致）：

1. **组件只用 `el-*`**，不要自己拼 Tailwind 的卡片/表格；
   颜色/圆角/间距只用 `--admin-*` 与 `--color-*` 令牌，不写死色值。
2. **不要静态 `import` element-plus**：`ElMessage` / `ElMessageBox` 统一从
   `@/utils/feedback` 引入（静态引入会把 1MB 的 Element Plus 塞进共享 chunk），
   模板里的 `el-*` 由后台布局动态注册，无需 import。

其它几条：

- **文案走 i18n**：命名空间 `admin.pluginPages.<pluginKey>.*`，公共文案复用
  `admin.pluginPages.common.*`；中英两份 locale 必须对称。新增文案用
  `python scripts/i18n_tool.py extract/apply`（不要手写一次性替换脚本）。
- **金额**用 `@/utils/money` 的 `formatMoney(amount, currency)`（符号 + 千分位 + 币种规范化），
  不要 `{{ amount }}` 裸渲染再单独摆一个币种文本。
- **危险操作**必须有二次确认（`ElMessageBox.confirm`），按钮给 `v-auth` 权限码。
- **日期**用 `@/utils/format` 的 `formatDateTime` / `formatDate`。

## 已知偏离（待收敛）

以下页面仍是「`el-*` + 手写 Tailwind」混用（数字为各自出现次数），
统一到 `el-*` 属于结构性重构，需要单独一轮（改动集中在模板，不影响数据逻辑）：

| 插件页                | `el-*` | 手写 Tailwind |
|--------------------|--------|-------------|
| `payment-gateway`  | 4      | 27          |
| `sms-provider`     | 4      | 28          |
| `enterprise`       | 1      | 19          |
| `compliance-audit` | 3      | 15          |
| `migration`        | 9      | 18          |
| `newsletter`       | 11     | 5           |
| `code-snippets`    | 17     | 22          |
| `approval`         | 12     | 8           |
| `popular-articles` | 5      | 10          |
| `article-likes`    | 0      | 7           |

建议顺序：先收敛"配置展示卡片"这类结构最简单的页（`sms-provider` / `payment-gateway` /
`compliance-audit` 的配置区），再处理含表格的页面。

## 前台插件页面

前台插件页面（若有）必须遵守前台约定：只用 `components/ui/*` + Tailwind + `--color-*` 令牌，
**不得**使用 `el-*`（前台走 SSR，不能为一次渲染加载 Element Plus）。
