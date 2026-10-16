/**
 * L1 区块注册表：区块名 → 组件
 *
 * 键必须与后端 `theme/blocks.py` 的 `ALLOWED_BLOCKS` 对齐 —— 后端是**白名单权威**
 * （能同时约束内置与第三方主题），这里决定"白名单里的哪些真的渲染得出来"。
 *
 * ## 三个白名单里有、但此处暂未注册的区块
 *
 * 它们会被 `BlockRenderer` **跳过并告警**（不是静默失败）：
 *
 *  - `site-nav`：导航已在 `site-header` 内联渲染，单独成块价值不大；
 *  - `tag-cloud`：需要标签列表接口，当前没有对应的公开端点；
 *  - `comment-list`：评论交互复杂（回复/点赞/分页），应作为 **L2 组件**或直接复用
 *    既有的 `CommentSection.vue`，不适合做成声明式区块。
 *
 * 要用它们时：后端白名单保留不动，在这里补注册即可。
 */
import type {Component} from 'vue'

import CategoryNavBlock from './CategoryNavBlock.vue'
import ColumnsBlock from './ColumnsBlock.vue'
import ContainerBlock from './ContainerBlock.vue'
import HeroBlock from './HeroBlock.vue'
import HtmlBlock from './HtmlBlock.vue'
import PageTitleBlock from './PageTitleBlock.vue'
import PaginationBlock from './PaginationBlock.vue'
import PostCardBlock from './PostCardBlock.vue'
import PostContentBlock from './PostContentBlock.vue'
import PostHeaderBlock from './PostHeaderBlock.vue'
import PostListBlock from './PostListBlock.vue'
import PostMetaBlock from './PostMetaBlock.vue'
import PostRelatedBlock from './PostRelatedBlock.vue'
import PostTagsBlock from './PostTagsBlock.vue'
import SearchBoxBlock from './SearchBoxBlock.vue'
import SectionBlock from './SectionBlock.vue'
import SidebarBlock from './SidebarBlock.vue'
import SiteFooterBlock from './SiteFooterBlock.vue'
import SiteHeaderBlock from './SiteHeaderBlock.vue'
import SpacerBlock from './SpacerBlock.vue'
import WidgetCategoriesBlock from './WidgetCategoriesBlock.vue'
import WidgetRecentBlock from './WidgetRecentBlock.vue'
import WidgetTagsBlock from './WidgetTagsBlock.vue'

export const BLOCK_COMPONENTS: Record<string, Component> = {
  // ── 布局容器 ──
  container: ContainerBlock,
  section: SectionBlock,
  columns: ColumnsBlock,
  // ── 站点框架 ──
  'site-header': SiteHeaderBlock,
  'site-footer': SiteFooterBlock,
  'search-box': SearchBoxBlock,
  // ── 首页 / 列表 ──
  hero: HeroBlock,
  'page-title': PageTitleBlock,
  'post-list': PostListBlock,
  'post-card': PostCardBlock,
  'category-nav': CategoryNavBlock,
  pagination: PaginationBlock,
  // ── 文章详情 ──
  'post-header': PostHeaderBlock,
  'post-meta': PostMetaBlock,
  'post-content': PostContentBlock,
  'post-tags': PostTagsBlock,
  'post-related': PostRelatedBlock,
  // ── 通用 ──
  html: HtmlBlock,
  spacer: SpacerBlock,
  // ── 侧栏与小工具（WP 经典主题的右侧栏）──
  sidebar: SidebarBlock,
  'widget-categories': WidgetCategoriesBlock,
  'widget-tags': WidgetTagsBlock,
  'widget-recent': WidgetRecentBlock,
}
