/**
 * 编辑页布局
 *
 * 三种模式，各自解决一个真实场景：
 *
 * | 模式 | 场景 |
 * |---|---|
 * | `classic` **经典** | 默认。字段、协作、历史都在手边，边写边配 |
 * | `focus` **专注** | 只留正文，收窄居中。长文写作时去掉一切干扰 |
 * | `split` **分栏预览** | 左写右看。Markdown 正文的实时效果，写完即见 |
 *
 * ## 为什么用 localStorage 而不是 URL 参数
 *
 * 布局是**个人偏好**，不是内容状态：同一个人反复打开同一篇文章，期望看到自己习惯的
 * 布局。做成 URL 参数的话，每次从列表点进来都会回到默认值 —— 那就等于没有记忆。
 *
 * ## 为什么容错读取
 *
 * localStorage 里的值可能来自旧版本（布局名改过）或被手工改坏。读到不认识的值时
 * **回落到默认**，而不是抛错或渲染出空白页。
 */

export type EditorLayout = 'classic' | 'focus' | 'split'

/** 三种布局的展示顺序（工具栏按钮按此顺序排列） */
export const EDITOR_LAYOUTS: readonly EditorLayout[] = ['classic', 'focus', 'split'] as const

const STORAGE_KEY = 'fb-editor-layout'
const DEFAULT_LAYOUT: EditorLayout = 'classic'

function isLayout(value: unknown): value is EditorLayout {
  return typeof value === 'string' && (EDITOR_LAYOUTS as readonly string[]).includes(value)
}

export function useEditorLayout() {
  const layout = ref<EditorLayout>(DEFAULT_LAYOUT)

  /** 从 localStorage 恢复（SSR 阶段没有 window，保持默认） */
  onMounted(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY)
      if (isLayout(saved)) layout.value = saved
    } catch {
      // 隐私模式下 localStorage 可能抛异常 —— 记忆失败不影响编辑
    }
  })

  function setLayout(next: EditorLayout): void {
    if (!isLayout(next)) return
    layout.value = next
    try {
      window.localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // 同上：存不进就算了，本次会话内仍然生效
    }
  }

  /** 循环切换（键盘快捷键用） */
  function cycleLayout(): void {
    const idx = EDITOR_LAYOUTS.indexOf(layout.value)
    setLayout(EDITOR_LAYOUTS[(idx + 1) % EDITOR_LAYOUTS.length] ?? DEFAULT_LAYOUT)
  }

  return {
    layout,
    setLayout,
    cycleLayout,
    /** 供模板判断用的计算属性（避免在模板里写字符串比较） */
    isClassic: computed(() => layout.value === 'classic'),
    isFocus: computed(() => layout.value === 'focus'),
    isSplit: computed(() => layout.value === 'split'),
  }
}
