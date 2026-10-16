/** 内容推荐接口（/api/v3/content/recommend）
 *
 * 对齐后端 `src/api/v3/modules/content/recommend/controller.py` 的 5 条路由：
 *   - GET /content/recommend/related/{article_id}   相关文章（公开）
 *   - GET /content/recommend/popular                热门文章（公开）
 *   - GET /content/recommend/trending-tags          热门标签（公开）
 *   - GET /content/recommend/for-me                 个性化推荐（登录）
 *   - GET /content/recommend/tags/{article_id}      标签建议（需 module_content:article:view）
 *
 * 字段全部来自 `src/api/v3/modules/content/recommend/service.py` 的真实返回体
 * （该模块无 schema.py，因此以 service 的返回结构为准）。
 */

import http from '../request'

/** 候选文章公共字段，对应 service.RecommendService._article_out */
export interface RecommendArticleItem {
  id: number
  /** 标题（articles.title） */
  title: string | null
  /** 别名（articles.slug） */
  slug: string | null
  /** 摘要（articles.excerpt） */
  excerpt: string | null
  /** 分类 id（articles.category） */
  category: number | null
  /** 标签（articles.tags_list 经 split_tags 归一） */
  tags: string[]
  /** 累计浏览（articles.views） */
  views: number
  /** 累计点赞（articles.likes） */
  likes: number
  /** 是否推荐位（articles.is_featured） */
  is_featured: boolean
  /** 发布时间（articles.published_at，ISO 串，可能为空） */
  published_at: string | null
}

/** 相关文章条目：附标签 Jaccard 相似度与综合得分 */
export interface RecommendRelatedItem extends RecommendArticleItem {
  /** 标签 Jaccard 相似度（service.related） */
  similarity: number
  /** 综合得分 = 相似度 ×0.7 + 同分类 ×0.2 + 热度 ×0.1 */
  score: number
}

/** 相关文章返回体（service.related） */
export interface RecommendRelatedResult {
  /** 作为基准的文章 id */
  article_id: number
  /** 基准文章的标签集合 */
  base_tags: string[]
  /** 命中候选总数（未截断前） */
  total: number
  items: RecommendRelatedItem[]
}

/** 热门文章条目：窗口统计时附窗口内真实浏览量 */
export interface RecommendPopularItem extends RecommendArticleItem {
  /** 指定 days 时按 page_views 统计的窗口内浏览量（累计模式无此字段） */
  window_views?: number
}

/** 热门文章返回体（service.popular） */
export interface RecommendPopularResult {
  /** 统计窗口天数；null 表示累计 articles.views 快照 */
  window_days: number | null
  /** 数据口径说明（后端原样文案） */
  source: string
  items: RecommendPopularItem[]
}

/** 热门标签条目（service.trending_tags） */
export interface RecommendTrendingTag {
  /** 标签文本 */
  tag: string
  /** 窗口内出现的已发布文章数 */
  count: number
}

/** 热门标签返回体（service.trending_tags） */
export interface RecommendTrendingTagsResult {
  window_days: number
  /** 窗口内不同标签总数 */
  total_tags: number
  items: RecommendTrendingTag[]
}

/** 个性化推荐条目：附打分分项（service.score_candidate） */
export interface RecommendScoredItem extends RecommendArticleItem {
  /** 加权总分 */
  score: number
  /** 标签兴趣匹配分（0..1） */
  tag_score: number
  /** 分类偏好分（0..1） */
  category_score: number
  /** 时效分（30 天半衰期，0..1） */
  recency_score: number
  /** 热度分（0..1） */
  popularity_score: number
}

/** 个性化推荐返回体（service.for_user） */
export interface RecommendForMeResult {
  /** 被推荐用户 id */
  user_id: number
  /** 参与画像计算的行为样本数 */
  behavior_samples: number
  /** 归一化后的兴趣标签权重，按权重倒序（[标签, 权重] 二元组） */
  interest_tags: Array<[string, number]>
  /** 冷启动标记：无任何行为样本时为 true */
  cold_start: boolean
  items: RecommendScoredItem[]
}

/** 标签建议条目（service.tag_suggestions） */
export interface RecommendTagSuggestion {
  /** 建议标签 */
  tag: string
  /** 关键词出现次数 */
  count: number
  /** 关键词权重分 */
  score: number
  /** 该标签是否已存在于标签库（任意已发布文章的 tags_list） */
  in_use: boolean
  /** 该标签是否已在本文的 current_tags 中 */
  already_on_article: boolean
}

/** 标签建议返回体（service.tag_suggestions） */
export interface RecommendTagSuggestionsResult {
  article_id: number
  /** 本文当前标签 */
  current_tags: string[]
  /** 标签库中的已知标签（最多 50 个） */
  known_tags: string[]
  suggestions: RecommendTagSuggestion[]
}

export const recommendApi = {
  /** 相关文章：按「标签相似度 ×0.7 + 同分类 ×0.2 + 热度 ×0.1」排序（公开） */
  related: (articleId: number, limit = 8) =>
    http.get<RecommendRelatedResult>(`/content/recommend/related/${articleId}`, {limit}),

  /** 热门文章：days 留空=累计 views 快照；指定=窗口内真实浏览量（公开） */
  popular: (days?: number, limit = 10) =>
    http.get<RecommendPopularResult>('/content/recommend/popular', {days, limit}),

  /** 热门标签：窗口内已发布文章的 tags_list 计数（公开） */
  trendingTags: (days = 30, limit = 20) =>
    http.get<RecommendTrendingTagsResult>('/content/recommend/trending-tags', {days, limit}),

  /** 个性化推荐：兴趣画像来自点赞 ×3 + 阅读 ×1，30 天衰减（登录） */
  forMe: (limit = 10) => http.get<RecommendForMeResult>('/content/recommend/for-me', {limit}),

  /** 标签建议：正文关键词 + 与标签库/本文的匹配情况（需 module_content:article:view） */
  tagSuggestions: (articleId: number, limit = 10) =>
    http.get<RecommendTagSuggestionsResult>(`/content/recommend/tags/${articleId}`, {limit}),
}
