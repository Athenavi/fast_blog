# fast_blog GDPR 前端接线 REPORT

> 说明：本批次是**并入既有页面**，不是新建。所有产出都在 `.gen/gdpr/` 下，
> 仓库内其它文件（`i18n/locales/`、`src/utils/menus.ts`、`src/api/index.ts`）
> 未改动，由父代理统一收口。

## 1. 端点 → API 函数 → 页面承载位置

| 后端端点（`controller.py`）                    | HTTP + 权限码（`codes.py`）                             | API 函数（`.gen/gdpr/api/gdpr.ts`）                       | 页面承载位置（`.gen/gdpr/pages/gdpr.vue`）                                                      |
|------------------------------------------|----------------------------------------------------|-------------------------------------------------------|-----------------------------------------------------------------------------------------|
| `/system/gdpr/compliance/check`          | `GET` / `module_system:gdpr:view`                  | `gdprApi.checkCompliance()` → `GdprComplianceReport`  | 「合规检查」标签页：`el-descriptions` 回显 `settings`，两张 `el-table`（GDPR / PCI DSS items + summary） |
| `/system/gdpr/compliance/cookie-consent` | `GET` / `module_system:gdpr:view`                  | `gdprApi.cookieConsent()` → `GdprCookieConsent`       | 「Cookie 同意横幅」标签页：生成按钮 + 只读 `el-input` 展示 `content` + 复制                                 |
| `/system/gdpr/compliance/privacy-policy` | `GET` / `module_system:gdpr:view`（query `as_html`） | `gdprApi.privacyPolicy(asHtml)` → `GdprPrivacyPolicy` | 「隐私政策」标签页：Markdown / HTML 两个生成按钮 + 只读 `el-input` 展示 `content` + 复制                      |

字段来源（逐条对照后端，无编造）：

- `checkCompliance` 返回：`generated_at` /
  `settings{retention_days,require_consent,allow_data_export,allow_data_deletion,contact_email,privacy_policy_url}` /
  `gdpr{items[{key,status,message,evidence}],summary{ok,warn,fail}}` / `pci_dss{同上}` —— 对应
  `compliance_service.checklist()`。
- `cookieConsent` 返回：`{site{name,url,contact_email,privacy_policy_url,retention_days}, content}` —— 对应
  `cookie_consent_html()`。
- `privacyPolicy` 返回：`{site{...}, format:'markdown'|'html', content}` —— 对应 `privacy_policy()`。

既有 3 个端点（`list` / `stats` / `remove`）原样保留，未改动。

## 2. 对既有文件的改动逐条清单

### `frontend/web/src/api/modules/gdpr.ts`（完整替换版 = 逐字保留 + 追加）

1. **追加**（在既有 3 个接口后、`export const gdprApi` 之前）：6 个 type
   `GdprCheckItem` / `GdprCheckSummary` / `GdprCheckGroup` / `GdprComplianceSettings` /
   `GdprComplianceReport` / `GdprSiteInfo` / `GdprPrivacyPolicy` / `GdprCookieConsent`。
2. **追加**（在 `gdprApi` 对象内 `remove` 行之后、对象 `}` 之前）：3 个方法
   `checkCompliance` / `privacyPolicy` / `cookieConsent`。
3. 既有 `GdprConsentItem` / `GdprConsentQuery` / `GdprStats` / `list` / `stats` / `remove`
   **逐字保留**，无删改。

### `frontend/web/src/pages/system/gdpr.vue`（完整替换版 = 逐字保留 + 追加）

共 **3 处追加，0 处删改既有行**：

1. **追加 import**：在既有 `import {gdprApi, ...} from '@/api'` 之后新增一行
   `import type {GdprCheckItem, GdprComplianceReport, GdprCookieConsent, GdprPrivacyPolicy} from '@/api'`。
   （既有 import 行本身未动；ESLint `import/order` 可能建议与上一行合并，属风格非错误。）
2. **追加 script 逻辑**：在既有 `onDelete()` 之后、`</script>` 之前新增
   `activeTab` / `compliance` / `complianceLoading` / `complianceFailed` /
   `cookieConsent` / `cookieLoading` / `privacyPolicy` / `privacyLoading` /
   `loadCompliance()` / `loadCookieConsent()` / `loadPrivacyPolicy()` /
   `statusLabelKey` / `checkTagType()` / `onTabChange()` / `copyText()`。
3. **追加 template 区块**：在既有 `</AdminListShell>` 之后、`</AdminPage>` 之前新增
   `<el-divider>` + `<el-tabs>`（三个 `el-tab-pane`：合规检查 / Cookie 同意横幅 / 隐私政策）。
   **未使用 `el-tabs` 包裹既有统计卡与列表**——既有结构保持原样，新内容整体后置追加。

既有 script / template / 统计卡 / `AdminListShell` / 各 `el-table-column` / `definePageMeta` / `onMounted(loadStats)`
**逐字保留**。既有页面无 `<style>`，本次追加也未新增 `<style>`，全部使用 Tailwind 原子类（`mb-*` / `flex` / `gap-*` /
`text-xs` / `text-fg-subtle` / `font-medium`）与 EP 组件。

## 3. 未接线端点及原因

- `POST /system/gdpr/consent`（访客上报 / 撤回同意，`controller.py` 第 68 行，`OptionalUser`，不要求登录）：
  **本次不接线**。它是**前台访客**动作，且生成的 Cookie 横幅 HTML（`cookie_consent_html`）已内嵌
  向该端点上报的逻辑，后台管理页无需再调用。不属于本次「后台 3 个 compliance 端点」范围。
- `GET /system/gdpr/consent` / `/consent/stats` / `DELETE /consent/{id}`：**已接线**（既有代码），未改动。

## 4. 存疑项

1. `el-tabs` 的 `@tab-change` 事件需 Element Plus **2.3+**。若项目 EP 版本更低，需改为 `@tab-click`
   （回退方案：改为在按钮点击时加载，已保证初始不自动请求，不影响「运行检查」按钮语义）。
2. 新类型需由父代理在 `frontend/web/src/api/index.ts` 第 74 行附近**补导出**
   （`export type {GdprCheckItem, GdprComplianceReport, GdprCookieConsent, GdprPrivacyPolicy} from './modules/gdpr'`
   ），否则页面 `import type ... from '@/api'` 会解析失败。
3. 新 i18n 键需由父代理并入 `i18n/locales/zh-CN.json` 与 `en.json` 的 `admin.system.gdpr` 节点；本 `i18n.json` **只含新增键
   **，未重复任何既有键。
4. `navigator.clipboard.writeText` 仅在安全上下文（HTTPS / localhost）可用；非安全上下文会走进 `copyFailed` 分支提示用户手动复制。
5. 合规检查的 `evidence` 字段（`Record<string, unknown>`）本次仅在类型层保留，未在 UI 展开渲染；如需展示可后续在检查项行内加展开/
   `el-popover`。
6. 未在 `onMounted` 自动调用合规端点（保持既有 `onMounted(loadStats)` 不变），首次进入标签页时经 `onTabChange`
   懒加载，或由用户点按钮触发。

## 5. 声明

**本产出未经编译 / 类型检查验证**：本子任务环境无法执行 `npm / nuxt / tsc / vue-tsc / git` 等任何 shell 命令，
上述文件未在真实构建中运行过。所有 `.vue` / `.ts` / `.json` 文本为按既有代码风格与后端契约静态编写，
接线正确性以父代理的编译与联调为准。
