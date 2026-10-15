/**
 * GraphQL 客户端（`POST /api/v3/graphql`）
 *
 * 后端在 `src/api/v3/graphql/` 提供读 + 少量写。**鉴权与 REST 完全同源**：同一个
 * `AuthControl`、同一套 `module_{域}:{模块}:{动作}` 权限码、API 令牌同样做
 * `scopes ∩ 用户权限` 收窄 —— 所以这里不做任何前端判权，401/403 由后端按 REST
 * 的语义返回，走 `request.ts` 既有拦截器（含 token 刷新）。
 *
 * ## 两个必踩的坑，写在这里省得下次再查
 *
 * 1. **字段名与参数名都是 camelCase**。后端用 strawberry 组 schema，其默认
 *    `auto_camel_case=True` 会把 Python 侧的 `page_size` / `category_id` /
 *    `cover_image` 暴露成 `pageSize` / `categoryId` / `coverImage`。
 *    查询串里写成 snake_case 会直接得到 `Cannot query field "page_size"` 的 400。
 * 2. **业务错误是 HTTP 200 + `errors` 数组**，不是 4xx。后端刻意把
 *    `NotFound/Conflict/Forbidden/BadRequest` 统一转成 GraphQL 错误且不回显堆栈，
 *    于是 `request.ts` 的拦截器（按 HTTP 状态码工作）**兜不住它们**。
 *    下面的 `gql()` 显式把 `errors` 转成 `Error`，让调用方的 `try/catch`
 *    与用 REST 时手感一致。
 *
 * ## 与 REST 的分工
 *
 * 只读查询、以及"一次拿多种资源"（例如首页要文章 + 分类 + 标签）用 GraphQL 更省往返；
 * **写操作仍以 REST 为主**，这里只暴露后端已实现的两个文章写接口，避免双 API 写语义分叉。
 */
import http from '../request'

// ---------------------------------------------------------------- 类型
// 与后端 `src/api/v3/graphql/types.py` 一一对应。后端刻意做了**显式白名单投影**
// （而不是把 service 的 dict 直接摊开），所以这里的字段集就是对外契约，
// 不会因为 service 内部演进被动变化。

export interface GqlCategory {
  id: number
  name: string
  slug?: string | null
  parentId?: number | null
}

export interface GqlTag {
  id: number
  name: string
  count?: number | null
}

export interface GqlViewer {
  id: number
  username: string
  email?: string | null
  isSuperuser: boolean
}

export interface GqlArticle {
  id: number
  title: string
  slug: string
  excerpt?: string | null
  coverImage?: string | null
  categoryId?: number | null
  tags: string[]
  views: number
  likes: number
  userId?: number | null
  status?: number | null
  hidden: boolean
  isFeatured: boolean
  isSticky: boolean
  isVipOnly: boolean
  requiredVipLevel: number
  postType?: string | null
  publishedAt?: string | null
  createdAt?: string | null
  updatedAt?: string | null
  /** 仅详情查询返回；列表查询为 null */
  content?: string | null
  languageCode?: string | null
  /** 详情专属：VIP 受限时正文为空且 `locked=true`（与 REST 公开详情同口径） */
  locked?: boolean | null
  /** 仅详情查询请求；后端用 DataLoader 批量加载，不会 N+1 */
  category?: GqlCategory | null
}

export interface GqlArticleConnection {
  items: GqlArticle[]
  total: number
  page: number
  pageSize: number
}

/** 创建/更新文章的输入（REST `ArticleCreate` 的子集；`title` 必填） */
export interface GqlArticleInput {
  title: string
  content?: string | null
  slug?: string | null
  excerpt?: string | null
  categoryId?: number | null
  tags?: string[] | null
  status?: number | null
  languageCode?: string | null
}

export interface GqlArticlesQuery {
  page?: number
  pageSize?: number
  keyword?: string
  status?: number
  categoryId?: number
}

export interface GqlPublicArticlesQuery {
  page?: number
  pageSize?: number
  categoryId?: number
  tag?: string
  keyword?: string
}

// ---------------------------------------------------------------- 字段选择集

/**
 * 列表用的文章字段。
 *
 * 刻意**不含** `content`（正文可能很大，列表用不上）与 `category`
 * （让列表只发一次 SQL；详情才顺着 DataLoader 取分类对象）。
 */
const ARTICLE_FIELDS = `
  id title slug excerpt coverImage categoryId tags views likes userId
  status hidden isFeatured isSticky isVipOnly requiredVipLevel postType
  publishedAt createdAt updatedAt
`

/** 详情用：在列表字段之上补正文、语言、VIP 锁标记与所属分类 */
const ARTICLE_DETAIL_FIELDS = `
  ${ARTICLE_FIELDS}
  content languageCode locked
  category { id name slug parentId }
`

/** 分页信封（与 REST 的 `items/total/page/page_size` 同名同义，减少两套心智） */
const CONNECTION_SELECTION = `total page pageSize items { ${ARTICLE_FIELDS} }`

// ---------------------------------------------------------------- 查询文档

const VIEWER_QUERY = `query { viewer { id username email isSuperuser } }`

const ARTICLES_QUERY = `
  query ($page: Int, $pageSize: Int, $keyword: String, $status: Int, $categoryId: Int) {
    articles(page: $page, pageSize: $pageSize, keyword: $keyword, status: $status, categoryId: $categoryId) {
      ${CONNECTION_SELECTION}
    }
  }
`

const ARTICLE_QUERY = `
  query ($id: Int!) {
    article(id: $id) { ${ARTICLE_DETAIL_FIELDS} }
  }
`

const PUBLIC_ARTICLES_QUERY = `
  query ($page: Int, $pageSize: Int, $categoryId: Int, $tag: String, $keyword: String) {
    publicArticles(page: $page, pageSize: $pageSize, categoryId: $categoryId, tag: $tag, keyword: $keyword) {
      ${CONNECTION_SELECTION}
    }
  }
`

const PUBLIC_ARTICLE_QUERY = `
  query ($id: Int, $slug: String) {
    publicArticle(id: $id, slug: $slug) { ${ARTICLE_DETAIL_FIELDS} }
  }
`

const CATEGORIES_QUERY = `
  query ($keyword: String) {
    categories(keyword: $keyword) { id name slug parentId }
  }
`

const TAGS_QUERY = `
  query ($limit: Int, $keyword: String) {
    tags(limit: $limit, keyword: $keyword) { id name count }
  }
`

const CREATE_ARTICLE_MUTATION = `
  mutation ($input: ArticleInput!) {
    createArticle(input: $input) { ${ARTICLE_DETAIL_FIELDS} }
  }
`

const UPDATE_ARTICLE_MUTATION = `
  mutation ($id: Int!, $input: ArticleInput!) {
    updateArticle(id: $id, input: $input) { ${ARTICLE_DETAIL_FIELDS} }
  }
`

// ---------------------------------------------------------------- 传输

/** GraphQL 响应信封；`errors` 非空即视为失败（即便 HTTP 是 200） */
interface GraphQLEnvelope<T> {
  data?: T | null
  errors?: Array<{ message: string; path?: Array<string | number> }>
}

/**
 * 发一次 GraphQL 请求并返回 `data`。
 *
 * 失败一律抛 `Error`（而不是返回 `{errors}`）：这样调用方对 GraphQL 与 REST
 * 用同一套 `try/catch`，不会出现"REST 要 catch、GraphQL 要查 errors"的分裂。
 */
async function gql<T>(query: string, variables?: Record<string, unknown>): Promise<T> {
  const envelope = await http.post<GraphQLEnvelope<T>>('/graphql', {query, variables})

  const errors = envelope?.errors
  if (errors?.length) {
    // 后端已把业务异常转成 GraphQL 错误；带上 path 便于定位是哪个字段失败
    const detail = errors.map((e) =>
      e.path?.length ? `${e.path.join('.')}: ${e.message}` : e.message,
    )
    throw new Error(detail.join('; '))
  }
  if (envelope?.data == null) {
    throw new Error('GraphQL 响应缺少 data')
  }
  return envelope.data
}

// ---------------------------------------------------------------- 对外 API

export const graphqlApi = {
  /** 当前身份；匿名返回 `null` */
  async viewer(): Promise<GqlViewer | null> {
    const data = await gql<{ viewer: GqlViewer | null }>(VIEWER_QUERY)
    return data.viewer
  },

  /** 管理端文章列表（需 `module_content:article:view`） */
  async articles(params: GqlArticlesQuery = {}): Promise<GqlArticleConnection> {
    const data = await gql<{ articles: GqlArticleConnection }>(ARTICLES_QUERY, {
      page: params.page ?? 1,
      pageSize: params.pageSize ?? 20,
      keyword: params.keyword ?? null,
      status: params.status ?? null,
      categoryId: params.categoryId ?? null,
    })
    return data.articles
  },

  /** 管理端文章详情（需 `module_content:article:view`；含正文） */
  async article(id: number): Promise<GqlArticle> {
    const data = await gql<{ article: GqlArticle }>(ARTICLE_QUERY, {id})
    return data.article
  },

  /** 公开文章列表（无需登录；仅已发布） */
  async publicArticles(params: GqlPublicArticlesQuery = {}): Promise<GqlArticleConnection> {
    const data = await gql<{ publicArticles: GqlArticleConnection }>(PUBLIC_ARTICLES_QUERY, {
      page: params.page ?? 1,
      pageSize: params.pageSize ?? 20,
      categoryId: params.categoryId ?? null,
      tag: params.tag ?? null,
      keyword: params.keyword ?? null,
    })
    return data.publicArticles
  },

  /**
   * 公开文章详情（无需登录）。
   *
   * `id` 与 `slug` 至少给一个，否则后端抛"必须提供 id 或 slug"。
   * VIP 受限时正文为空且 `locked=true`。
   */
  async publicArticle(params: { id?: number; slug?: string }): Promise<GqlArticle> {
    const data = await gql<{ publicArticle: GqlArticle }>(PUBLIC_ARTICLE_QUERY, {
      id: params.id ?? null,
      slug: params.slug ?? null,
    })
    return data.publicArticle
  },

  /** 分类列表（公开） */
  async categories(keyword?: string): Promise<GqlCategory[]> {
    const data = await gql<{ categories: GqlCategory[] }>(CATEGORIES_QUERY, {
      keyword: keyword ?? null,
    })
    return data.categories
  },

  /** 标签列表（公开） */
  async tags(params: { limit?: number; keyword?: string } = {}): Promise<GqlTag[]> {
    const data = await gql<{ tags: GqlTag[] }>(TAGS_QUERY, {
      limit: params.limit ?? 200,
      keyword: params.keyword ?? null,
    })
    return data.tags
  },

  /** 创建文章（需 `module_content:article:create`）；内部仍走既有 article_service */
  async createArticle(input: GqlArticleInput): Promise<GqlArticle> {
    const data = await gql<{ createArticle: GqlArticle }>(CREATE_ARTICLE_MUTATION, {input})
    return data.createArticle
  },

  /** 更新文章（需 `module_content:article:edit`） */
  async updateArticle(id: number, input: GqlArticleInput): Promise<GqlArticle> {
    const data = await gql<{ updateArticle: GqlArticle }>(UPDATE_ARTICLE_MUTATION, {id, input})
    return data.updateArticle
  },
}
