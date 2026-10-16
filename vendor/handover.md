# fast_blog 未完成事项

> 更新时间：2026-10-16
> **本文件只列尚未完成的事。** 已完成的工作（后端 v3、前端接线 100%、CI 修复、Meilisearch 可配置、
> 三款主题重构与实装、安装向导、审批闸门与 MCP、SAML、GraphQL 客户端、编辑器与渲染修复）见 git log，
> 不在此复述。

---

## 1. 待补依赖（会直接导致 CI 失败）

- [ ] **`pyproject.toml` 缺 `pysaml2` / `xmlsec`**
  本机为 SAML 断言校验装了它们（连带 `lxml`），但没写进依赖声明 → **CI 上 SAML 测试会因缺依赖失败**。
- [ ] **`cryptography` 版本不一致**
  本机被 pip 由 `48.0.0` 升到 `50.0.2`，而 `requirements.txt` 钉 `44.0.0`。
  `xmlsec 1.3.17` 与 `44.0.0` 的组合**未在干净环境实测过**（本机环境证明不了）。

## 2. 未验证（需运行中的后端 / 浏览器 / 外部服务）

- [ ] **CI 在 `main` 上是否变绿** —— 按用户指示未合并 `vue3 → main`、未推送。`main` 落后 `vue3` 205 个提交，
  且另有 4 个提交不在 `vue3` 里。
- [ ] **`npm ci` 在 Linux 上实际通过** —— 本机是 Windows 且 Docker 不可用，只能静态确认 lock 内容。
- [ ] **Meilisearch 的真实行为** —— 连通性探测、索引读写、可见性过滤的实际效果、事件订阅者被触发时是否同步成功。
  本环境**无 Meilisearch 实例**，所有结论来自代码与测试。
- [ ] **三款主题在浏览器里的观感** —— 切主题后页面是否真的换掉、后台改「主色」后样式是否即时变化。
  ⚠️ 看到效果的前提：`frontend/site/` 是新增目录，需 **prescan**（`npm run dev` 的 `predev`，或 `npm run build`）
  才复制进 `.plugin-pages/` —— **光刷新浏览器不够**。
- [ ] **SAML 与真实 IdP 的端到端握手**、ACS 签发登录态的 DB 往返（测试用的是假会话）。
- [ ] **主题运行时接管的视觉回归**：`e2e/visual.spec.ts` 的基线未重跑。
- [ ] **a11y 基线 26 处违规收到 0**（阻塞：需可跑后端 + 超管凭据）。
  四类违规：`button-name`（admin-dashboard/menu/ops-backup/plugin 的纯图标按钮）、`label`（admin-media/user/role）、
  `scrollable-region-focusable`（横向滚动表格容器需 `tabindex="0"`）、`color-contrast`
  （site-categories/site-search/admin-menu）。

## 3. 未做的功能（真实缺口）

- [ ] **`page_builder` 可视化与前端渲染器** —— 目前是 JSON 直通，没有拖拽编排，也没有前台渲染。
- [ ] **富文本协作编辑器** —— `collaboration` 的 CRDT 后端是真的，但前端编辑器是纯 textarea。
- [ ] **容器备份 / 恢复** —— 失败，镜像里缺 `pg` 客户端。
- [ ] **Prometheus / OpenTelemetry 端点** —— 没有指标导出。
- [ ] **`ErrorState` 之外的前台空/错态覆盖**、**代码高亮按需执行**：已做其中一部分，剩余零散页面未扫。
- [ ] **三个巨型管理页的拆分**（原计划用 fleet 串行委派，因目标变更中止，零产出）：
  `analytics/seo.vue`（1804 行 / 12 tab）、`system/translation.vue`（1773 / 6 tab）、`system/monitoring.vue`（1581 / 8 tab）。
- [ ] **主题的区块级组合** —— 当前只支持**页面级**整页接管；区块级（多主题混搭）是预留方向，未做。
- [ ] **安装向导 `single` 模式的成功路径** —— `enterprise`（默认）下写口一律 403 已验证；`single` 的端到端未跑。
- [ ] **文档陈旧**：README 版本号、`docs/DEPLOYMENT.md` 的"只有一个迁移"（实际 8 个、head `e5f1b8c93a07`）、
  postman collection 的 base path 仍是 `/api/v1`。
- [ ] **`vendor/handover.md` 之外的交接材料**（本文件已精简为纯待办）。

## 4. 刻意不做（**不是缺口，别为了数字归零去接**）

- **24 条 FastApiAdmin 兼容别名**：`/list`、`/detail/{id}`、`/create`、`/update/{id}`、`/delete`、
  `/system/permission/capabilities`、`/system/role/permission/{id}` —— 前端走 REST 主路径，不需要它们。
- **3 条第三方支付回调**：`commerce/payment/callback/{id}`、`commerce/tipping/callback/{id}`、`mobile/vip/callback/{id}`
  —— 前端无承载场景。

> ⚠️ **前后端端点缺口测绘的一个已知误报源**：文本正则的**跨行引号配对错位**（`translation.ts` 里注释的反引号
> 会吞掉整段代码路径），曾把 21 个**已接**的 translation 端点误判为缺失、得出"499 缺口"的错误结论。
> 正确的做法是**逐行**提取引号内字符串，不要跨行匹配。

## 5. 未提交

- [ ] **本会话全部改动仍在工作区**（含本文件），未提交 —— 由用户自行提交。
- [ ] **工作分支是 `vue3`**，不是 `main`；CI 只在 `main` / `master` / `V*` tag 触发。
