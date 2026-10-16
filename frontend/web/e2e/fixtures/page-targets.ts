/**
 * 视觉回归 / a11y 巡检的页面清单（UI/UX 路线图 Batch 0.1–0.2）
 *
 * 选页原则：
 *   - 只挑**结构稳定**（已迁移 `AdminListShell` / `AdminPage` 骨架，或本身就是稳定壳）的页面，
 *     以免把正在重构中的页面变成噪音；
 *   - `ready` 必须是「数据与骨架都就绪」后才出现的元素 —— 否则会拍到骨架屏/加载态；
 *   - 动态区域（时间、统计数字、表格行）由 `visual.spec.ts` 用 `mask` 屏蔽。
 *
 * 加页面的姿势：先在本地 `npx playwright test e2e/visual.spec.ts --update-snapshots`
 * 生成基线，再提交基线与清单改动一起进仓库。
 */

export interface PageTarget {
  /** 截图文件名与 a11y 基线键（保持稳定，不要随标题改） */
  slug: string
  /** 报告里显示的中文名 */
  name: string
  /** 路由路径 */
  path: string
  /** 属于后台布局（已登录，`layouts/admin.vue`） */
  admin?: boolean
  /** 就绪选择器；后台默认 `.layout__main`，前台默认 `#__nuxt` */
  ready?: string
}

export const PAGE_TARGETS: PageTarget[] = [
  // ---------------------------------------------------------------- 后台
  {slug: 'admin-dashboard', name: '后台·仪表盘', path: '/dashboard', admin: true},
  {slug: 'admin-article-list', name: '后台·文章列表', path: '/content/article', admin: true},
  {slug: 'admin-article-new', name: '后台·新建文章', path: '/content/article/new', admin: true},
  {slug: 'admin-media', name: '后台·媒体库', path: '/content/media', admin: true},
  {slug: 'admin-category', name: '后台·分类', path: '/content/category', admin: true},
  {slug: 'admin-user', name: '后台·用户', path: '/system/user', admin: true},
  {slug: 'admin-role', name: '后台·角色', path: '/system/role', admin: true},
  {slug: 'admin-menu', name: '后台·菜单', path: '/system/menu', admin: true},
  {slug: 'admin-setting', name: '后台·设置', path: '/system/setting', admin: true},
  {slug: 'admin-analytics-report', name: '后台·统计报表', path: '/analytics/report', admin: true},
  {slug: 'admin-ops-backup', name: '后台·备份', path: '/ops/backup', admin: true},
  {slug: 'admin-plugin', name: '后台·插件', path: '/extension/plugin', admin: true},

  // ---------------------------------------------------------------- 前台
  {slug: 'site-home', name: '前台·首页', path: '/'},
  {slug: 'site-articles', name: '前台·文章列表', path: '/articles'},
  {slug: 'site-categories', name: '前台·分类', path: '/categories'},
  {slug: 'site-search', name: '前台·搜索', path: '/search'},
]

/** 后台页面的就绪选择器（`layouts/admin.vue` 的 el-main 类名，Element Plus 懒加载完成后才出现） */
export const ADMIN_READY = '.layout__main'

export function readySelector(target: PageTarget): string {
  if (target.ready) return target.ready
  return target.admin ? ADMIN_READY : '#__nuxt'
}
