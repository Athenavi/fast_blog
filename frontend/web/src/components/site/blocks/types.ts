/**
 * L1 区块协议类型
 *
 * 与后端 `src/api/v3/modules/extension/theme/blocks.py` 的 `ALLOWED_BLOCKS` **一一对应**：
 * 后端是权威白名单（能同时约束内置与第三方主题），这里只做前端侧的类型描述与防御性查表。
 *
 * 新增区块要同时改两处 —— 这是刻意的：区块集合是可枚举、可审查的契约。
 */

/** 一个区块节点（后端已归一化：未知区块不会出现在这里） */
export interface BlockNode {
  /** 区块名，对应 `registry.ts` 的键 */
  block: string
  /** 区块参数（后端已校验：字符串不含 `;{}/*<>`，且长度受限） */
  props?: Record<string, unknown>
  /** 子区块 —— 容器类区块（section / columns / container）用插槽接收 */
  children?: BlockNode[]
  /** 可选样式钩子：主题在 `styles.css` 里可定向 `.class` */
  class?: string
}

/** 页面上下文：透传给需要页面数据的区块（文章详情页的 post-header / post-content 等） */
export interface BlockContext {
  /** 当前文章（详情页才有） */
  article?: Record<string, unknown>

  [key: string]: unknown
}

/** 所有区块组件共同接收的 props（由 BlockRenderer 统一注入） */
export interface BlockProps {
  /** 解析后的区块参数 */
  propsData: Record<string, unknown>
  /** 页面上下文 */
  context: BlockContext
  /** 主题给该区块的样式钩子 */
  blockClass?: string
}
