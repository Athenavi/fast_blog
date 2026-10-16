/**
 * 后台列表页组合式（`useTable` 的超集，后者已改为本模块的兼容别名）
 *
 * 把列表页反复要写的逻辑收敛到一处：
 *   查询/分页 · 加载与错误 · 空态判断 · 行选择与批量操作 · URL 查询同步 · 删除后页码回退
 *
 * 返回对象是 `useTable` 的**超集**（保留 `list` / `load` / `remove` 等旧字段），
 * 因此既有页面无需改动；新页面用更强的新字段：
 *
 *   const list = useAdminList<ArticleItem, ArticleQuery>({
 *     fetcher: (params) => articleApi.list(params),
 *     defaultQuery: { keyword: '', status: undefined },
 *     syncUrl: true,
 *   })
 *   list.rows / list.selection / list.selectedCount / list.hasFilters / list.isEmpty …
 */

import {computed, onMounted, reactive, ref, type Ref} from 'vue'

import type {PageQuery, PageResult} from '@/api/types'

export interface UseAdminListOptions<T, Q extends PageQuery> {
  /** 拉数据的函数（通常直接传 `xxxApi.list`） */
  fetcher: (params: Q) => Promise<PageResult<T>>
  /** 查询条件默认值（`reset()` 会恢复到这里） */
  defaultQuery?: Partial<Q>
  /** 每页条数，默认 20 */
  pageSize?: number
  /** 是否挂载后立即加载，默认 true */
  immediate?: boolean
  /** 是否把查询条件与分页同步到 URL（刷新后保持筛选、链接可分享） */
  syncUrl?: boolean
  /** 行唯一键，默认 'id' */
  rowKey?: string
}

/** URL query 里一切都是字符串，这里按原值类型还原 */
function coerce(current: unknown, raw: unknown): unknown {
  if (raw === undefined || raw === null || raw === '') return undefined
  const text = Array.isArray(raw) ? String(raw[0]) : String(raw)
  if (text === '') return undefined
  if (typeof current === 'number') {
    const parsed = Number(text)
    return Number.isNaN(parsed) ? undefined : parsed
  }
  if (typeof current === 'boolean') return text === 'true' || text === '1'
  return text
}

export function useAdminList<T, Q extends PageQuery = PageQuery>(
  options: UseAdminListOptions<T, Q>,
) {
  // 这两个是 Nuxt 自动导入的 composable（必须在 setup 内调用本函数）
  const route = options.syncUrl ? useRoute() : null
  const router = options.syncUrl ? useRouter() : null

  const loading = ref(false)
  const rows = ref([]) as Ref<T[]>
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(options.pageSize ?? 20)
  /** 最近一次加载是否失败（页面可据此展示错误态） */
  const failed = ref(false)

  const defaults = {...(options.defaultQuery ?? {})} as Record<string, unknown>
  const query = reactive({...defaults}) as Q

  // ---- 首次进入时从 URL 还原筛选（让刷新与分享链接保留状态）
  if (route) {
    for (const key of Object.keys(defaults)) {
      const restored = coerce(defaults[key], route.query[key])
      if (restored !== undefined) (query as Record<string, unknown>)[key] = restored
    }
    const rawPage = Number(route.query.page ?? '')
    if (Number.isFinite(rawPage) && rawPage > 0) page.value = rawPage
    const rawSize = Number(route.query.page_size ?? '')
    if (Number.isFinite(rawSize) && rawSize > 0) pageSize.value = rawSize
  }

  /** 当前是否有生效的筛选条件（用于"清除筛选"按钮与空态文案） */
  const hasFilters = computed(() =>
    Object.entries(query as Record<string, unknown>).some(([key, value]) => {
      if (value === undefined || value === null || value === '') return false
      return value !== defaults[key]
    }),
  )

  const isEmpty = computed(() => !loading.value && rows.value.length === 0)

  function buildParams(): Record<string, unknown> {
    const params: Record<string, unknown> = {page: page.value, page_size: pageSize.value}
    for (const [key, value] of Object.entries(query as Record<string, unknown>)) {
      if (value === undefined || value === null || value === '') continue
      params[key] = value
    }
    return params
  }

  function syncToUrl(mode: 'push' | 'replace' = 'push'): void {
    if (!router) return
    const next: Record<string, string> = {}
    for (const [key, value] of Object.entries(buildParams())) {
      if (key === 'page' && value === 1) continue
      next[key] = String(value)
    }
    // 默认 push：筛选/翻页要能"后退回去"（此前用 replace，按后退会直接离开列表页）
    if (mode === 'replace') void router.replace({query: next})
    else void router.push({query: next})
  }

  /**
   * 请求序号：快速翻页或连续搜索时，先发的慢响应可能后到并覆盖新结果
   * （表现为列表"闪回旧数据"）。每次 load 取新序号，响应回来时序号过期就丢弃。
   */
  let requestSeq = 0

  async function load(): Promise<void> {
    const seq = (requestSeq += 1)
    loading.value = true
    failed.value = false
    try {
      const result = await options.fetcher(buildParams() as Q)
      if (seq !== requestSeq) return
      rows.value = (result?.items ?? []) as T[]
      total.value = result?.total ?? 0
      // 换了数据页，当前页的勾选自然失效；但跨页累积的 id 集合要保留
      selection.value = []
    } catch {
      // 错误提示由 request 拦截器统一处理，这里只保证表格状态干净
      if (seq !== requestSeq) return
      rows.value = []
      total.value = 0
      failed.value = true
    } finally {
      if (seq === requestSeq) loading.value = false
    }
  }

  /** 从第一页重新查询（搜索按钮 / 条件变化）；筛选变了，之前的勾选不再适用 */
  function search(): Promise<void> {
    page.value = 1
    clearSelection()
    syncToUrl()
    return load()
  }

  /** 恢复默认查询条件并重新查询 */
  function reset(): Promise<void> {
    for (const key of Object.keys(query)) delete (query as Record<string, unknown>)[key]
    Object.assign(query as Record<string, unknown>, options.defaultQuery ?? {})
    page.value = 1
    clearSelection()
    syncToUrl()
    return load()
  }

  function onPageChange(next: number): Promise<void> {
    page.value = next
    syncToUrl()
    return load()
  }

  function onSizeChange(next: number): Promise<void> {
    pageSize.value = next
    page.value = 1
    syncToUrl()
    return load()
  }

  // ---- 行选择（跨页保留）
  /**
   * 分两层：
   *  - `selection`：**当前页**被勾选的行（el-table 的 selection-change 直接给这个）；
   *  - `selectedIds`：**跨页累积**的 id 集合（批量操作真正作用的对象）。
   * 此前只有当前页，翻页即丢 —— 50 条数据要分 3 次选、3 次删。
   */
  const rowKey = options.rowKey ?? 'id'
  const selection = ref([]) as Ref<T[]>
  const selectedIds = ref<number[]>([])
  const selectedCount = computed(() => selectedIds.value.length)
  /** 当前页选中数：用于提示"已选 N 项（含其它页）" */
  const pageSelectionCount = computed(() => selection.value.length)

  function idOf(row: T): number {
    return (row as Record<string, unknown>)[rowKey] as number
  }

  function onSelectionChange(selected: T[]): void {
    selection.value = selected
    const pageIds = rows.value.map(idOf)
    const pageSelected = new Set(selected.map(idOf))
    // 当前页取消的移出集合，当前页新选的加入，**其它页原样保留**
    const next = selectedIds.value.filter((id) => !pageIds.includes(id))
    for (const id of pageIds) if (pageSelected.has(id)) next.push(id)
    selectedIds.value = next
  }

  function clearSelection(): void {
    selection.value = []
    selectedIds.value = []
  }

  /**
   * 带二次确认的操作（删除、批量删除等）
   * 若当前页只剩一条且不是第一页，操作后自动回退一页，避免出现空页。
   */
  async function remove(
    action: () => Promise<unknown>,
    // 默认文案仅供兜底：store 层没有 i18n 上下文，调用方应传入已翻译的文案
    message = '确定要执行该操作吗？',
    title = '确认操作',
    successText = '操作成功',
  ): Promise<boolean> {
    const {ElMessage, ElMessageBox} = await import('element-plus')
    try {
      await ElMessageBox.confirm(message, title, {type: 'warning'})
    } catch {
      return false
    }

    try {
      await action()
      ElMessage.success(successText)
      // 被操作的行多半已不存在，清空跨页勾选避免"删过了还显示已选"
      clearSelection()
      if (rows.value.length === 1 && page.value > 1) page.value -= 1
      await load()
      return true
    } catch {
      return false
    }
  }

  if (options.immediate !== false) {
    onMounted(load)
  }

  return {
    // 推荐命名
    rows,
    selection,
    selectedIds,
    selectedCount,
    pageSelectionCount,
    onSelectionChange,
    clearSelection,
    hasFilters,
    isEmpty,
    failed,
    reload: load,
    // 兼容 useTable 的旧命名
    list: rows,
    load,
    total,
    page,
    pageSize,
    query,
    search,
    reset,
    onPageChange,
    onSizeChange,
    remove,
    loading,
  }
}
