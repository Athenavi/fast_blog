/**
 * 后台用到的 Element Plus 图标。
 *
 * ## 为什么要单独一个文件、而且要**静态具名导入**
 *
 * 先试过在 `layouts/admin.vue` 里写
 * `const {Odometer, Document, ...} = await import('@element-plus/icons-vue')`，
 * 以为具名解构能让 Rollup 裁剪 —— **实测不成立**：动态 `import()` 返回的是整个模块
 * 命名空间，Rollup 无法据此判断"只用到这几个"，产物里那张 icons chunk 依旧是完整的
 * 166 KB raw / 42 KB gzip（预算脚本的口径 2 会直接把 `DIw1XUY7.js 42KB` 列出来）。
 *
 * 裁剪只在**静态 import + 具名使用**时才生效。所以把清单落在这里（本模块是静态导入），
 * 再由 `admin.vue` 用动态 `import()` 加载**这个模块**——既拿到裁剪，又不会因为
 * `layouts/` 属于 app 层而把图标塞进前台的初始包。
 *
 * 新增图标时改这里一处即可（`admin.vue` 只消费 `adminIcons`）。
 */
import {
  ArrowDown,
  Bell,
  Briefcase,
  Brush,
  ChatDotRound,
  Coin,
  Collection,
  DataLine,
  Delete,
  Document,
  Edit,
  Expand,
  Files,
  Fold,
  Grid,
  Lock,
  MagicStick,
  Menu,
  Money,
  Moon,
  Odometer,
  Plus,
  Promotion,
  Refresh,
  Search,
  Setting,
  Sunny,
  Tools,
  Top,
  User,
} from '@element-plus/icons-vue'
import type {Component} from 'vue'

/**
 * 侧边栏与头部按**字符串名**引用图标（`menu.icon` → `<component :is="..."/>`），
 * 因此需要一个"名字 → 组件"的注册来源。这里按下标暴露数组，
 * `admin.vue` 用每个图标的 `name` 属性注册成全局组件。
 */
export const adminIcons: Component[] = [
  ArrowDown,
  Bell,
  Briefcase,
  Brush,
  ChatDotRound,
  Coin,
  Collection,
  DataLine,
  Delete,
  Document,
  Edit,
  Expand,
  Files,
  Fold,
  Grid,
  Lock,
  MagicStick,
  Menu,
  Money,
  Moon,
  Odometer,
  Plus,
  Promotion,
  Refresh,
  Search,
  Setting,
  Sunny,
  Tools,
  Top,
  User,
]
