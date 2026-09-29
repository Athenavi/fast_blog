# mobile 域剩余 2 个端点接线报告

批次范围：把后端 v3 `mobile` 域剩余 2 个缺失端点接到 `frontend/web`。

| 端点                                               | 鉴权  | 承接函数                                      |
|--------------------------------------------------|-----|-------------------------------------------|
| `GET /api/v3/mobile/category/tree`               | 无   | `mobileApi.categoryTree()`                |
| `POST /api/v3/mobile/media/upload/article-cover` | 需登录 | `mobileApi.mediaUploadArticleCover(file)` |

---

## ① 端点 → 函数 → 承载位置

| 端点                                        | 前端函数                                                                      | 承载文件                                                                  | 说明                                                                                                                                 |
|-------------------------------------------|---------------------------------------------------------------------------|-----------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| `GET /mobile/category/tree`               | `mobileApi.categoryTree(): Promise<CategoryItem[]>`                       | `src/api/modules/mobile.ts`（仅 API 层）                                  | 无 UI 承载：前端已有等价端点消费方（见下），本次只补 API 封装，不新增页面                                                                                          |
| `POST /mobile/media/upload/article-cover` | `mobileApi.mediaUploadArticleCover(file: File): Promise<MobileMediaItem>` | `src/api/modules/mobile.ts` + `src/components/site/ArticleEditor.vue` | 封面承载在投稿编辑器：`pickCover()` 由 `mobileApi.mediaUpload`（`/upload/image`）改走 `mobileApi.mediaUploadArticleCover`（`/upload/article-cover`） |

交付物（均在 `frontend/web/.gen/mobile_gaps/`）：

- `api/mobile.ts` —— `src/api/modules/mobile.ts` 的**完整替换版**（逐字保留既有内容 + 追加 2 个方法）。
- `components/site/ArticleEditor.vue` —— `src/components/site/ArticleEditor.vue` 的**完整替换版**（唯一改动：`pickCover()`
  换用新端点，并同步注释）。
- `i18n.json` —— `{}`（无需新增文案，见 ③）。
- `REPORT.md` —— 本文件。

---

## ② 字段来源逐条对照

### `GET /mobile/category/tree`

后端 `mobile/category/controller.py::category_tree`：

```python
return resp.success(await category_service.tree(db, is_visible=True))
```

- `category_service.tree()`（`content/category/service.py`）→ `build_tree(list_categories(is_visible=True))`。
- 数组元素是 `_out(category)` 的字典，键固定为：
  `id`、`name`、`slug`、`description`、`parent_id`、`sort_order`、`icon`、`color`、`is_visible`、`articles_count`、`created_at`、
  `updated_at`、`children`（`children` 递归同结构）。

前端类型 `CategoryItem`（`src/api/modules/category.ts`）逐条对应：

| 后端键              | 前端 `CategoryItem`              | 状态 |
|------------------|--------------------------------|----|
| `id`             | `id: number`                   | ✓  |
| `name`           | `name: string`                 | ✓  |
| `slug`           | `slug?: string \| null`        | ✓  |
| `description`    | `description?: string \| null` | ✓  |
| `parent_id`      | `parent_id?: number \| null`   | ✓  |
| `sort_order`     | `sort_order: number`           | ✓  |
| `icon`           | `icon?: string \| null`        | ✓  |
| `color`          | `color?: string \| null`       | ✓  |
| `is_visible`     | `is_visible: boolean`          | ✓  |
| `articles_count` | `articles_count: number`       | ✓  |
| `created_at`     | `created_at?: string \| null`  | ✓  |
| `updated_at`     | `updated_at?: string \| null`  | ✓  |
| `children`       | `children: CategoryItem[]`     | ✓  |

结论：字段**完全对齐**，无需扩展类型，直接复用既有 `CategoryItem`（从 `./category` 导入）。

### `POST /mobile/media/upload/article-cover`

后端 `mobile/media/controller.py`：

```python
async def _store(current, db, file):
    results = await media_service.upload_files(db, user_id=current.id, files=[(file.filename, await file.read())])
    return results[0] if results else {}

@router.post("/upload/article-cover", ...)
async def upload_article_cover(db, user=..., file: UploadFile = File(...)):
    """与 ``/upload/image`` 同一实现，语义别名（移动端封面场景）"""
    return resp.success(await _store(user, db, file), msg="上传成功")
```

请求（multipart）：字段名 **`file`**（单文件，`UploadFile = File(...)`）——与 `mediaUpload` 完全一致。

响应：统一信封 `{code, msg, data}`，`data` 即 `_store` 的返回（`upload_files` 的 `results[0]`）。逐层回溯 `upload_files`（
`content/media/service.py` L176-223）：

```python
result = await process_single_file(processor, file_data, filename, db)
data = result.get("data") or {}
data["success"] = True
results.append(data)
```

而 `process_single_file`（`src/utils/upload/public_upload.py` L1028-1115）**只返回**
`{'success': True, 'hash', 'media_id', 'storage_path'}`（**无 `data` 键**）。

因此 `data = {}` → 实际返回负载为 `{"success": true}`。

> 前端声明类型沿用既有 `MobileMediaItem`（与 `mediaUpload` 一致），这是**类型声明层面的稳定契约**；
> 但按当前后端实现，运行时 `data` 只含 `{success: true}`，**不含 `file_url` / `id` / `filename`**。
> 消费方（`ArticleEditor.pickCover` 读 `uploaded.file_url`、`MediaPickerDialog.onFileChange` 读 `item.file_url`）
> 在当前后端下会拿到 `undefined`。此为**既有**行为（`/mobile/media/upload/image` 同样如此），本批次**未引入也未修复**，
> 详见 ④ 存疑项。

### `article-cover` 与 `upload/image` 的差异核对（任务要点 2）

| 维度      | `POST /mobile/media/upload/image`                                                             | `POST /mobile/media/upload/article-cover`        | 差异      |
|---------|-----------------------------------------------------------------------------------------------|--------------------------------------------------|---------|
| 处理实现    | `_store` → `media_service.upload_files`                                                       | 同一个 `_store`                                     | **无**   |
| 校验      | `FileProcessor(allowed_mimes=app_config.ALLOWED_MIMES, allowed_size=app_config.UPLOAD_LIMIT)` | 同一 `FileProcessor`、同一配置                          | **无**   |
| 尺寸 / 比例 | 无封面专属尺寸校验                                                                                     | 无封面专属尺寸校验                                        | **无**   |
| 返回字段    | `resp.success(results[0], msg="上传成功")`                                                        | 同                                                | **无**   |
| 请求字段名   | `file`                                                                                        | `file`                                           | **无**   |
| 鉴权      | 需登录（`jwt_required_dependency`）                                                                | 需登录                                              | **无**   |
| 唯一差异    | ——                                                                                            | 路径 `/upload/article-cover`、summary "上传文章封面（需登录）" | 路径与语义标签 |

结论：两端点在后端是**同一实现的语义别名**（controller docstring 原文："与 `/upload/image` 同一实现，语义别名"
）。不存在尺寸、校验或返回结构上的差异。前端因此按"独立端点、独立封装、语义对齐"处理。

### `mobile/category/tree` 与既有等价方法的差异核对（任务要点 1）

前端既有分类端点：

| 既有方法                            | 路径                              | 鉴权 / 权限                                      | 可见性过滤                           |
|---------------------------------|---------------------------------|----------------------------------------------|---------------------------------|
| `categoryApi.tree(is_visible?)` | `/content/category/tree`        | `CurrentUser` + `AuthControl(CATEGORY_VIEW)` | `is_visible` 可选，**默认返回全部**（含隐藏） |
| `categoryApi.publicTree()`      | `/content/category/public/tree` | 无鉴权                                          | 强制 `is_visible=True`            |
| `categoryApi.publicList()`      | `/content/category/public`      | 无鉴权                                          | 强制 `is_visible=True`（分页列表）      |
| `mobileApi`（改造前）                | ——                              | ——                                           | **无分类相关方法**                     |

后端实现对照：

```python
# content/category/controller.py::public_category_tree
return resp.success(await category_service.tree(db, is_visible=True))

# mobile/category/controller.py::category_tree
return resp.success(await category_service.tree(db, is_visible=True))
```

两者调用**同一个 `category_service.tree`、同一个 `is_visible=True`、同一响应形状** —— 即
`GET /mobile/category/tree` 与既有 `GET /content/category/public/tree` **字节级等价**。

判定：这是后端提供的移动端**别名端点**。处理方式是**在 `mobileApi` 新增 `categoryTree()` 按 mobile 域路径封装，但不新增任何消费点
**（既有页面/组合式函数继续用 `categoryApi.publicTree()` / `categoryApi.tree()`），以避免重复的 UI 语义。
`mobileApi.categoryTree()` 的 jsdoc 中已显式标注这层等价关系。

> 若评审要求严格去重，可让 `categoryApi.publicTree()` 与 `mobileApi.categoryTree()` 共用同一实现，或在后端移除该别名端点；本批次不擅自改动既有
`categoryApi` 的语义。

---

## ③ 未接线及原因

- **`i18n.json` 为空 `{}`**：本次接线未引入任何新 UI 文案。封面承载复用了既有键 `myPosts.coverUploaded` /
  `myPosts.coverUploadFailed`（`zh-CN.json` / `en.json` 均已存在），`mobileApi.categoryTree()` 无 UI 消费点。故无需新增键，双语无新增即天然对称。
- **`MediaPickerDialog.vue` 不承载 `article-cover`**：该组件是通用图片选择器（`RichEditor` 插图等场景），上传的是**任意图片
  **而非文章封面，调用 `/upload/article-cover` 会造成语义错配。封面上传的承载点是 `ArticleEditor.pickCover()`，已在该文件处理。
- **未新增分类树消费页面**：见 ②（等价端点已由既有页面消费），避免重复语义。
- **后端其它 mobile 端点（如 `GET /mobile/category/list`）不在本批次 2 个端点之内**，未改动，如实记录以备后续批次。

---

## ④ 存疑项

1. **上传响应 `data` 缺少媒体字段（高优先级，需父代理核实）**
   按 `process_single_file` 的返回值，`/mobile/media/upload/image` 与 `/mobile/media/upload/article-cover` 的实际
   `data` 均为 `{"success": true}`，不含 `file_url` / `id` / `filename`。
   前端 `mediaUpload` / `mediaUploadArticleCover` 声明为 `MobileMediaItem`，与运行时形状不一致；
   下游 `uploaded.file_url` 会取到 `undefined`。
    - 这正是 `content/media/service.py::upload_files` 里 `result.get("data")` 与 `process_single_file`
      返回结构不匹配的结果（webhook 中 `data.get("id")` / `data.get("file_size")` 同样恒为 `None`）。
    - 本批次**未修改任何后端文件**（写入边界限制），也**未修改 `mediaUpload` 既有声明**（保持一致）。是否属后端需修的真实缺陷，交父代理判断。
2. **`mobile/category/tree` 的语义重复**：与 `content/category/public/tree`
   完全等价，是否为后端刻意保留的移动端别名、抑或冗余端点，需产品/后端确认（本批次按"封装但零消费点"处理）。
3. **分类树端点是否需要登录态**：后端 `mobile/category/tree` 无鉴权（`db: DBSession` 即可）。前端 `categoryTree()`
   同样不带任何凭据，与后端一致；若后续该端点加鉴权，仅需调用方保证登录态，API 封装无需改。

---

## ⑤ 未经编译验证声明

**本批次产出未经过任何编译 / 类型检查 / 运行验证，亦未在真实环境请求端点。**

- 子代理**无 shell 权限**，无法运行 `npm run typecheck`、`vue-tsc`、`pnpm build` 或任何端点冒烟测试。
- 产出保证的仅是：人工逐字核对后的**完整文件**（非 diff / 非片段）、LF 行尾、导入闭合（`api/mobile.ts` 的 `CategoryItem` 已导入；
  `ArticleEditor.vue` 既有 `mobileApi` 导入不变）、未使用 `as` 掩盖类型、未引入 mock/编造数据。
- `MobileMediaItem` / `CategoryItem` 类型是否与**运行时真实响应**一致，见 ④ 存疑项 1（该项未经运行验证，仅为**源码静态推断
  **）。
- 合并到仓库后**必须**由父代理执行一次类型检查与一次上传冒烟（登录后 `POST /mobile/media/upload/article-cover` 传 `file`
  ）后再判定是否可用。

---

## ⑥ 需父代理在 `src/api/index.ts` 追加的 re-export 块

**无需追加任何 re-export。** 依据：

- `mobileApi` 已在 `src/api/index.ts` 第 349 行导出（`export {mobileApi} from './modules/mobile'`）；新增方法是该对象的属性，自动可见。
- `categoryTree()` 的返回类型 `CategoryItem` 已在第 274 行导出（
  `export type {CategoryItem, CategoryPayload} from './modules/category'`）。
- `mediaUploadArticleCover()` 的返回类型 `MobileMediaItem` 已在第 358 行导出。

即：`mobile.ts` 的完整替换版**新增了 1 处模块内 import**（`import type {CategoryItem} from './category'`），
这属于 `modules/mobile.ts` 内部依赖，**不产生新的对外类型导出，因此 `index.ts` 无需改动**。

落位动作（父代理执行）：

1. 用 `frontend/web/.gen/mobile_gaps/api/mobile.ts` 覆盖 `frontend/web/src/api/modules/mobile.ts`。
2. 用 `frontend/web/.gen/mobile_gaps/components/site/ArticleEditor.vue` 覆盖
   `frontend/web/src/components/site/ArticleEditor.vue`。
3. `i18n.json` 为 `{}`，无需合并任何 i18n 键。
4. 运行一次 `typecheck`；与 ④.1 的后端问题一并决策。
