/**
 * 编辑页的视图模式
 *
 * 三种模式，各自回答一个不同的问题：
 *
 * | 模式 | 回答的问题 |
 * |---|---|
 * | `edit` **编辑** | 「我正在写」—— 只给正文，横向空间全留给文字 |
 * | `split` **分栏** | 「我写的这段排出来长什么样」—— 左写右看，看的是**当前缓冲区** |
 * | `read` **阅读** | 「读者会看到什么」—— 整栏给渲染结果，宽度与前台一致 |
 *
 * ## 为什么取代原来的 classic / focus / split
 *
 * 那三个里 `focus` 与 `classic` 的差别只是「收不收窄」，而收窄已经由工作台正文栏的
 * 阅读宽度默认给出来了；`split` 与新的 `split` 同义。留着等于用三个名字描述两种状态。
 *
 * ## 为什么存 localStorage 而不是 URL 参数
 *
 * 视图模式是**个人偏好**，不是内容状态：同一个人反复打开文章，期望看到自己习惯的
 * 那一档。做成 URL 参数的话，每次从列表点进来都会回到默认值 —— 那就等于没有记忆，
 * 还会让「分享编辑页链接」这件事多出一个没人需要的维度。
 *
 * ## 为什么容错读取
 *
 * 存过的值可能来自旧版本（模式名换过）或被手工改坏。读到不认识的值时**回落到默认**，
 * 而不是抛错或渲染出一屏空白。
 */

export type DocViewMode = 'edit' | 'split' | 'read'

/** 三种模式的展示顺序（顶栏分段控件按此顺序排列） */
export const DOC_VIEW_MODES: readonly DocViewMode[] = ['edit', 'split', 'read'] as const

const STORAGE_KEY = 'fb-doc-view-mode'
const DEFAULT_MODE: DocViewMode = 'edit'

function isMode(value: unknown): value is DocViewMode {
  return typeof value === 'string' && (DOC_VIEW_MODES as readonly string[]).includes(value)
}

export function useDocViewMode() {
  const mode = ref<DocViewMode>(DEFAULT_MODE)

  /** 从 localStorage 恢复（SSR 阶段没有 window，保持默认） */
  onMounted(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY)
      if (isMode(saved)) mode.value = saved
    } catch {
      // 隐私模式下 localStorage 可能抛异常 —— 记忆失败不影响编辑
    }
  })

  function setMode(next: DocViewMode): void {
    if (!isMode(next)) return
    mode.value = next
    try {
      window.localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // 同上：存不进就算了，本次会话内仍然生效
    }
  }

  return {
    mode,
    setMode,
    /** 供模板判断用的计算属性（避免在模板里写字符串比较） */
    isEdit: computed(() => mode.value === 'edit'),
    isSplit: computed(() => mode.value === 'split'),
    isRead: computed(() => mode.value === 'read'),
  }
}
