/**
 * 分页表格组合式
 *
 * 把「查询条件 / 分页 / 加载 / 删除确认 / 删除后页码回退」这些每个列表页都要写的逻辑收敛到一处，
 * 页面只需给出 `fetcher` 与查询字段，其余交给它。
 *
 * 用法：
 *   const { list, loading, total, page, pageSize, query, search, reset, load, onPageChange, remove }
 *     = useTable({ fetcher: (params) => userApi.list(params), defaultQuery: { is_active: undefined } })
 */

import {onMounted, reactive, ref, type Ref} from 'vue'

import type {PageQuery, PageResult} from '@/api/types'

/** 动态引入确认框：同样避免 element-plus 进入前台共享 chunk */
async function confirmBox(message: string, title = '提示'): Promise<boolean> {
  try {
    const {ElMessageBox} = await import('element-plus')
    await confirmBox(message, title)
    return true
  } catch {
    return false
  }
}


/** 动态引入 Element Plus 的消息提示：避免 element-plus 进入前台共享 chunk */
async function notify(
  kind: 'error' | 'warning' | 'success' | 'info',
  message: string,
): Promise<void> {
  try {
    const {ElMessage} = await import('element-plus')
    ElMessage({type: kind, message})
  } catch {
    /* 提示失败不应影响主流程 */
  }
}


export interface UseTableOptions<T, Q extends PageQuery> {
  /** 拉取数据的函数（通常直接传某个 xxxApi.list） */
  fetcher: (params: Q) => Promise<PageResult<T>>
  /** 查询条件默认值（reset() 会恢复到这里的值） */
  defaultQuery?: Partial<Q>
  /** 每页条数，默认 20 */
  pageSize?: number
  /** 是否创建后立即加载，默认 true */
  immediate?: boolean
}

export function useTable<T, Q extends PageQuery = PageQuery>(options: UseTableOptions<T, Q>) {
  const loading = ref(false)
  const list = ref([]) as Ref<T[]>
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(options.pageSize ?? 20)

  const query = reactive({...(options.defaultQuery ?? {})}) as Q

  async function load(): Promise<void> {
    loading.value = true
    try {
      const params = {
        ...query,
        page: page.value,
        page_size: pageSize.value,
      } as Q
      const result = await options.fetcher(params)
      list.value = result.items ?? []
      total.value = result.total ?? 0
    } catch {
      // 错误提示由 request 拦截器统一处理，这里只保证表格状态干净
      list.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  /** 从第一页重新查询（搜索按钮 / 条件变化） */
  function search(): Promise<void> {
    page.value = 1
    return load()
  }

  /** 恢复默认查询条件并重新查询 */
  function reset(): Promise<void> {
    Object.keys(query).forEach((key) => {
      delete (query as Record<string, unknown>)[key]
    })
    Object.assign(query as Record<string, unknown>, options.defaultQuery ?? {})
    return search()
  }

  function onPageChange(nextPage: number): Promise<void> {
    page.value = nextPage
    return load()
  }

  function onSizeChange(nextSize: number): Promise<void> {
    pageSize.value = nextSize
    page.value = 1
    return load()
  }

  /**
   * 带二次确认的操作（删除、恢复等）
   * 若当前页只剩一条且不是第一页，删除后自动回退一页，避免出现空页。
   */
  async function remove(
    action: () => Promise<unknown>,
    message = '确定要执行该操作吗？',
    title = '确认操作',
    successText = '操作成功',
  ): Promise<boolean> {
    try {
      await confirmBox(message, title)
    } catch {
      return false
    }

    try {
      await action()
      void notify('success', successText)
      if (list.value.length === 1 && page.value > 1) {
        page.value -= 1
      }
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
    loading,
    list,
    total,
    page,
    pageSize,
    query,
    load,
    search,
    reset,
    onPageChange,
    onSizeChange,
    remove,
  }
}
