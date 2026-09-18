# FastBlog 管理后台（frontend/web）

Vue 3 + Vite + TypeScript + Pinia + Vue Router + Element Plus + Tailwind CSS 4。
结构参考 FastApiAdmin 的 `frontend/web`，API 全部对接本项目自有的 **v3 API**（`src/api/v3`）。

## 快速开始

```bash
npm install
npm run dev        # http://localhost:5173
```

开发期由 Vite 把 `/api` 代理到后端（默认 `http://localhost:9421`，见 `.env.development` 的
`VITE_PROXY_TARGET`）。

```bash
npm run build      # 产物输出到 dist/
npm run type-check # vue-tsc 类型检查
npm run preview    # 预览构建产物
```

生产环境由 nginx 把 `/api/` 反代到后端，前端只提供静态文件（与 `frontend-astro` 的部署方式一致）。

## 与后端 API 的关系

- **只使用 v3**：请求前缀固定为 `/api/v3`（`VITE_API_BASE_URL`），不再有 v2 回退逻辑
- **统一响应**：`{ code, msg, data, pagination }`；`code === 200` 为成功
  （见 `src/api/types.ts`，与后端 `src/api/v3/common/response.py` 一致）
- **鉴权**：登录成功后 token 存 localStorage，请求头带 `Authorization: Bearer <token>`，
  401 时会用 refresh token 静默续期一次（`src/api/request.ts`）
- **权限码**：与后端 `capabilities.code` 完全一致（`resource:action`，如 `article:create`）

## 目录结构

```
src/
├── api/                 按域拆分的接口层（request.ts 为统一客户端）
│   ├── request.ts       axios 封装：token 注入、401 续期、错误提示
│   ├── types.ts         v3 响应契约
│   └── modules/*.ts     auth / user / role / menu / article / ... 共 21 个模块
├── components/          通用组件（后续按需补充）
├── constants/           常量（存储键、路由白名单等）
├── directives/          v-auth / v-role 权限指令
├── layouts/             布局（DefaultLayout + Sidebar + Header）
├── router/
│   ├── routes.ts        路由表（含 meta.permission）
│   ├── index.ts         createRouter + 动态注册
│   └── guard.ts         登录态、权限过滤、动态路由、403
├── store/modules/       user（会话/权限）/ permission（菜单）/ app（UI 状态）
├── styles/              全局样式 + Tailwind
├── utils/               工具（storage 等）
└── views/               页面（login / dashboard / error / placeholder）
```

## 菜单与权限的设计取舍（重要）

后台菜单由**前端路由表 + 用户权限码过滤**生成（`src/store/modules/permission.ts`），
而不是由后端菜单表驱动。原因是 fast_blog 的 `menus` / `menu_items` 是**前台导航菜单**
（供主题渲染），不具备后台「菜单 ↔ 权限码」语义；后台权限的权威来源是 `capabilities.code`。
这与 FastApiAdmin 的 `sys_menu` 单表模型不同，属于有意取舍。

权限判断有两层：

1. **页面级**：路由 `meta.permission` 与 `/system/auth/me` 返回的权限码比对，不通过则跳 403
2. **元素级**：`v-auth="'article:create'"`（数组为 AND 语义），超级管理员直接放行

## 当前进度

- Phase 7（已完成）：工程骨架、请求层、21 个 API 模块、登录/权限/菜单/守卫链路、
  布局与仪表盘；`npm run build` 与 `npm run type-check` 均通过
- Phase 8（进行中）：把 `/content`、`/system`、`/analytics`、`/extension`、`/ops`
  下约 20 个页面从占位替换为真实实现（占位页见 `src/views/placeholder`）
