# marketing/form 公开端点前端接线报告

工作区：`X:\project\fast_blog`。本次仅产出 `.gen/form_public/` 下的文件，未改动仓库中任何其它文件。

## ① 端点 → 函数 → 页面位置

| 后端端点（`src/api/v3/modules/marketing/form/controller.py`）                 | 前端函数（`api/form.ts`）                | 页面位置                                                      |
|-------------------------------------------------------------------------|------------------------------------|-----------------------------------------------------------|
| `GET /api/v3/marketing/form/public/{slug}`（无鉴权，`public_form`）           | `formApi.publicForm(slug)`         | `pages/forms/[slug].vue` 的 `useAsyncData` → `apiGet`（SSR） |
| `POST /api/v3/marketing/form/public/{slug}/submit`（无鉴权，`public_submit`） | `formApi.publicSubmit(slug, data)` | `pages/forms/[slug].vue` 的 `onSubmit()`（客户端）              |

页面文件：`frontend/web/.gen/form_public/pages/forms/[slug].vue`。
路由落在 `/forms/:slug`。

**路径选择说明**：后端公开端点以 **slug** 寻址（`public_form(slug: str)` / `public_submit(slug: str)`），
不是数字 `form_id`——故参数名取 `[slug]`，URL 为 `/forms/<slug>`（而非 `/forms/<id>`）。
`definePageMeta({layout: 'default'})`，采用前台默认布局与既有 `apiGet`（`$fetch`）SSR 范式。

**是否需要加入前台导航**：不需要，且本子任务未改动导航（`SiteHeader.vue` 未触碰）。
理由：公开表单是「按 slug 直达的落地页」（运营把链接投放到外部渠道），不是常驻导航项；
`SiteHeader` 的导航在后台配置了 `main-nav` 时以后台配置为准，运营可按需自行加入，无需在此硬编码。

## ② 字段来源逐条对照（均来自后端 schema/service，无编造）

页面渲染所依据的每个字段都来自 `schema.py` 的 `FormFieldOut` / `FormOut`：

| 前端用法                                                              | 来源                                                                                   | 说明                                                                                                |
|-------------------------------------------------------------------|--------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| `field.label` → 控件标签、错误信息、**提交键**                                 | `FormFieldOut.label`                                                                 | 提交键必须用 label，见下                                                                                   |
| `field.field_type` → 控件类型分支                                       | `FormFieldOut.field_type`                                                            | 取值域 `text\|textarea\|email\|number\|select\|checkbox\|radio\|date`（`FormFieldCreate` 的 `pattern`） |
| `field.placeholder`                                               | `FormFieldOut.placeholder`                                                           |                                                                                                   |
| `field.help_text`                                                 | `FormFieldOut.help_text`                                                             | 渲染为字段下方说明                                                                                         |
| `field.required`                                                  | `FormFieldOut.required`                                                              | 客户端必填校验 + `*` 标记                                                                                  |
| `field.options` → `parseOptions()`（按 `,` 拆分）                      | `FormFieldOut.options`                                                               | 后端注释：`select/checkbox/radio 的选项，逗号分隔`                                                             |
| `field.default_value`                                             | `FormFieldOut.default_value`                                                         | 见 ④ 存疑项（页面未显式套用默认值）                                                                               |
| `form.title` / `form.description`                                 | `FormOut.title` / `FormOut.description`                                              | 页头标题与描述                                                                                           |
| `form.submit_message`                                             | `FormOut.submit_message`                                                             | 提交成功后展示（缺省回退 i18n `publicForm.success`）                                                           |
| 提交回执 `result.accepted` / `result.stored` / `result.submission_id` | `service.public_submit` 返回 `{"accepted": True, "stored": ..., "submission_id": ...}` | 判断成功与否                                                                                            |

**提交请求体的键（关键）**：`service.public_submit` 执行 `value = data.get(f.label)`，
即后端以**字段 label 字符串**作为 `data` 的键。因此 `onSubmit()` 构造
`data[f.key] = ...`，其中 `f.key = field.label`。这不是猜测，而是 service 的取值方式决定的。

**错误信息形状**：后端必填失败抛 `BadRequestError(f"必填项未填写: {f.label}")`，
前端 `fieldRequired` 文案与之语义对齐（客户端先做同样判定，同时保留后端返回的兜底）。

## ③ 未接线及原因

- 管理端 8 个端点（`GET/POST/PUT/DELETE /marketing/form`、字段 CRUD、提交列表/删除）本次**不改动**，
  `api/form.ts` 中既有后台方法逐字保留。
- 无「重复提交后端去重」「验证码」类端点：controller/service 中**不存在**，故前端不做相关调用；
  重复提交仅在**客户端**用 `submitting` / `submitted` 状态阻断（见 ④）。
- 未新增前台导航项、未改 `SiteHeader.vue`（理由见 ①）。
- 未改 `src/api/index.ts`（超出写入边界）：所需的 re-export 块见 ⑥，请父代理追加。

## ④ 存疑项

1. **`default_value` 未套用**：`FormFieldOut.default_value` 存在，但公开页当前一律以空串初始化
   （`model[f.key] = ''`）。原因是需要确认「默认值」是否应在公开填写页预填——若确认要预填，
   在 `watch(localFields)` 初始化处改为 `model[f.key] = f.default_value ?? ''`（checkbox 组需另做拆分）。
   目前选择「不预填」，以免用户不自知地带着默认值提交。
2. **单个复选框的提交值**：schema 未规定单复选框的值格式。页面用 `'1'` / `''` 表示勾选/未勾选。
   后端必填判定为 `f.required and (value is None or str(value).strip() == "")`——
   注意 `str(False)` / `str('False')` 非空，若发送布尔 `false` 反而会「通过」必填。
   故发字符串 `'1'`/`''` 以与后端判定一致。
3. **复选框多选提交格式**：多个选中项以逗号拼接为单个字符串（后端 `options` 亦以逗号分隔，
   故选项文本内不含逗号，拼接可逆）。若后续要求数组形态，需同步调整前端与展示端。
4. **label 唯一性依赖**：因提交键是 label，同表单内重复 label 会在 `data` 中互相覆盖，
   后端也未做唯一约束。这是后端设计固有的约束，前端未加拦截。
5. **无服务端去重/限流/验证码**：service 未实现，前端仅做客户端防重复点击，
   无法阻止脚本重复提交。

## ⑤ 未经编译验证声明

本子任务**无 shell 权限**，所有产物**未经过任何编译 / 类型检查 / 运行时验证**：
未运行 `npm run build`、`vue-tsc`、`nuxi typecheck` 或任何 lint。
以下为**编译前即依赖父代理补齐**的项：

- 页面 `import {… FormPublicDetail, FormPublicField …} from '@/api'` 需要 ⑥ 的 re-export 才能解析类型
  （`formApi` 值已由现有 `export {formApi}` 提供）。
- i18n 键 `publicForm.*` 需并入 `i18n/locales/zh-CN.json` 与 `en.json` 后方可生效（文件内容见 `i18n.json`）。
- 页面文件需从 `.gen/form_public/pages/forms/[slug].vue` 落到 `frontend/web/src/pages/forms/[slug].vue`。

## ⑥ 需父代理在 `src/api/index.ts` 追加的 re-export 块

`formApi` 值已由现有 `export {formApi} from './modules/form'` 导出，**无需重复导出**。
仅需补上三个新类型。可在现有 `// ---- 批次 2` 的 form 段落内，追加：

```ts
export type {FormPublicDetail, FormPublicField, FormPublicSubmitResult} from './modules/form'
```

（或直接把这 3 个名字并入该段既有的 `export type { FormFieldItem, … } from './modules/form'` 花括号中。）

## 落地清单

| 产物                       | 目标位置                                                                |
|--------------------------|---------------------------------------------------------------------|
| `api/form.ts`            | 覆盖 `frontend/web/src/api/modules/form.ts`                           |
| `pages/forms/[slug].vue` | 新建 `frontend/web/src/pages/forms/[slug].vue`                        |
| `i18n.json`              | 将 `publicForm` 段并入 `frontend/web/i18n/locales/zh-CN.json`、`en.json` |
| ⑥ 的 re-export            | 追加到 `frontend/web/src/api/index.ts`                                 |
